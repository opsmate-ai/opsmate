from typing import Callable, Any, Dict, Awaitable, Union, List, Set, Optional
from enum import Enum
from pydantic import BaseModel, Field
from opsmate.dino import dino
from collections import deque
import asyncio
import structlog

logger = structlog.get_logger(__name__)


class WorkflowType(Enum):
    PARALLEL = "parallel"
    SEQUENTIAL = "sequential"
    NONE = "none"


class WorkflowContext:
    def __init__(self, results: Dict[str, Any] = {}, input: Dict[str, Any] = {}):
        self.results = results
        self.input = input
        self._lock = asyncio.Lock()

    async def set_result(self, key: str, value: Any):
        async with self._lock:
            self.results[key] = value

    def __repr__(self):
        return f"WorkflowContext({self.results})"


class Step:
    step_bags = {}

    def __init__(
        self,
        fn: Callable[[WorkflowContext], Awaitable[Any]] = None,
        op: WorkflowType = WorkflowType.NONE,
        steps: List["Step"] = [],
        prev: Optional[Set["Step"]] = None,
    ):
        self.fn = fn
        self.fn_name = fn.__name__ if fn else None
        self.steps: List[Step] = steps
        if prev:
            self.prev = prev
        else:
            self.prev = set(self.steps)
        self.op = op

    def __or__(self, other: "Step") -> "Step":
        if self.op == WorkflowType.PARALLEL and other.op == WorkflowType.PARALLEL:
            return Step(
                op=WorkflowType.PARALLEL,
                steps=self.steps + other.steps,
            )
        elif self.op == WorkflowType.PARALLEL and other.op == WorkflowType.NONE:
            return Step(
                op=WorkflowType.PARALLEL,
                steps=self.steps + [other],
            )
        elif self.op == WorkflowType.NONE and other.op == WorkflowType.PARALLEL:
            return Step(
                op=WorkflowType.PARALLEL,
                steps=[self] + other.steps,
            )
        else:
            return Step(
                op=WorkflowType.PARALLEL,
                steps=[self, other],
            )

    def __rshift__(self, other: "Step") -> "Step":
        seq_step = Step(
            op=WorkflowType.SEQUENTIAL,
            prev=set([self]),
            steps=[self, other],
        )
        other.prev.add(seq_step)
        return seq_step

    def topological_sort(self):
        sorted = []
        visited = set()

        def visit(step: Step):
            if step in visited:
                return
            if step.op == WorkflowType.NONE:
                sorted.append(step)
            elif step.op == WorkflowType.PARALLEL:
                for child in step.steps:
                    visit(child)
                sorted.append(step)
            elif step.op == WorkflowType.SEQUENTIAL:
                assert len(step.steps) == 2
                step_a, step_b = step.steps
                visit(step_a)
                sorted.append(step)
                visit(step_b)

        visit(self)
        return sorted

    def __repr__(self):
        if self.fn_name:
            return f"Step({self.fn_name})"
        else:
            return f"Step({self.op})"


def _tree_from_step(root: Step):
    nodes, edges = set(), set()

    def build(node: Step):
        if node not in nodes:
            nodes.add(node)
            if node.op == WorkflowType.PARALLEL:
                for child in node.steps:
                    ch = build(child)
                    edges.add((ch, node))

                return node
            elif node.op == WorkflowType.SEQUENTIAL:
                assert len(node.steps) == 2
                step_a, step_b = node.steps

                l = build(step_a)
                r = build(step_b)
                edges.add((l, node))
                edges.add((node, r))
                return r
            elif node.op == WorkflowType.NONE:
                return node

    build(root)
    return nodes, edges


def draw_dot(root, format="svg", rankdir="TB"):
    from graphviz import Digraph

    assert rankdir in ["TB", "LR"]
    nodes, edges = _tree_from_step(root)
    dot = Digraph(format=format, graph_attr={"rankdir": rankdir})
    for node in nodes:
        dot.node(name=str(id(node)), label=str(node), shape="record")
    for n1, n2 in edges:
        dot.edge(str(id(n1)), str(id(n2)))
    return dot


class Workflow:
    def __init__(self, root: Step, semerphore_size: int = 1):
        self.root = root
        self.steps = deque(root.topological_sort())
        self._semerphore_size = semerphore_size
        self._semaphore = asyncio.Semaphore(semerphore_size)
        self._lock = asyncio.Lock()
        self._init_prevs()

    def _init_prevs(self):
        """
        Initialize the prevs dictionary with the prevs of each step.
        Not use the prevs of the step itself because we want the workflow to be re-runnable.
        """
        self.prevs = {}
        for step in self.steps:
            self.prevs[str(id(step))] = step.prev.copy()

    async def _run_step(self, step: Step, ctx: WorkflowContext):
        async with self._semaphore:
            logger.info("Running step", step=str(step), step_op=step.op)
            if step.op == WorkflowType.NONE:
                result = await step.fn(ctx)
            else:
                result = None
            async with self._lock:
                for rest_step in self.steps:
                    rest_step_id = str(id(rest_step))
                    if step in self.prevs[rest_step_id]:
                        self.prevs[rest_step_id].remove(step)

        await ctx.set_result(step.fn_name, result)
        return result

    async def run(self, ctx: WorkflowContext = None):
        while len(self.steps) > 0:
            step = self.steps.popleft()
            await self._run_step(step, ctx)


def step(fn: Callable):
    _step = Step(fn)
    Step.step_bags[_step.fn_name] = _step.fn

    return _step


class Location(BaseModel):
    city: str = Field(description="The city name")


@step
@dino("gpt-4o-mini", response_model=Location)
async def do_a(ctx):
    return f"Home town of {ctx.input["person_a"]}"


@step
@dino("gpt-4o-mini", response_model=Location)
async def do_b(ctx):
    return f"Home town of {ctx.input["person_b"]}"


@step
@dino("gpt-4o-mini", response_model=str)
async def do_c(ctx):
    """
    You are very good at estimating the distance between two cities.
    """
    a_result = ctx.results["do_a"]
    b_result = ctx.results["do_b"]
    return f"The distance between {a_result.city} and {b_result.city}"


@step
@dino("gpt-4o-mini", response_model=str)
async def do_d(ctx):
    return "Hello"


@step
@dino("gpt-4o-mini", response_model=str)
async def do_e(ctx):
    return "Hello"


async def main():
    root = (do_a | do_b) | (do_c | do_d) >> do_e

    sorted = root.topological_sort()

    for step in sorted:
        print(step)

    dot = draw_dot(root, rankdir="LR")
    dot.render("workflow", view=False)

    workflow = Workflow(root)
    ctx = WorkflowContext(input={"person_a": "Elon Musk", "person_b": "Boris Johnson"})
    await workflow.run(ctx)
    print(ctx.results)

    workflow = Workflow(root)
    ctx = WorkflowContext(input={"person_a": "Elon Musk", "person_b": "Boris Johnson"})
    await workflow.run(ctx)
    print(ctx.results)
    # print(
    #     await workflow.run(
    #         WorkflowContext(
    #             input={"person_a": "Elon Musk", "person_b": "Boris Johnson"}
    #         )
    #     )
    # )


if __name__ == "__main__":
    asyncio.run(main())
