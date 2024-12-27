from typing import Callable, Any, Dict, Awaitable, List, Set, Optional
from enum import Enum
from collections import deque
import asyncio
import structlog
import uuid
from collections import defaultdict

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
        self.id = str(uuid.uuid4()).split("-")[0]
        self.fn = fn
        self.fn_name = fn.__name__ if fn else None
        self.steps: List[Step] = steps.copy()
        if prev:
            self.prev = prev.copy()
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

    def __rshift__(self, right: "Step") -> "Step":
        seq_step = Step(
            op=WorkflowType.SEQUENTIAL,
            steps=[self],
        )

        for step in right.__all_orphan_children():
            if seq_step not in step.prev:
                step.prev.add(seq_step)
                step.steps.append(seq_step)

        return right

    def __all_orphan_children(self):
        result = []
        if self.op == WorkflowType.NONE and self.steps == []:
            return [self]
        else:
            for step in self.steps:
                result.extend(step.__all_orphan_children())
        return result

    def topological_sort(self):
        nodes = {}
        edges = defaultdict(list)

        def build(node: Step):
            node_id = str(id(node))
            if node_id not in nodes:
                nodes[node_id] = node
                for child in node.steps:
                    build(child)
                    # points from child to parent for the purpose of topological sort
                    edges[str(id(child))].append(node_id)

        build(self)

        visited = set()
        stack = deque()

        def visit(node_id: str):
            if node_id in visited:
                return
            visited.add(node_id)

            for parent_id in edges[node_id]:
                if parent_id not in visited:
                    visit(parent_id)
            stack.appendleft(node_id)

        for node_id in nodes:
            if node_id not in visited:
                visit(node_id)

        nodes = [nodes[node_id] for node_id in stack]
        return nodes

    def __repr__(self):
        if self.fn_name:
            return f"Step({self.fn_name}-{self.id})"
        else:
            return f"Step({self.op}-{self.id})"


def _tree_from_step(root: Step):
    nodes, edges = set(), set()

    def build(node: Step):
        if node not in nodes:
            nodes.add(node)
            for child in node.steps:
                build(child)
                edges.add((child, node))

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
    def __init__(self, root: Step, semerphore_size: int = 4):
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
            logger.info(
                "Running step",
                step=str(step),
                step_op=step.op,
                prev_size=len(self.prevs[str(id(step))]),
            )
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
        round = 0
        while len(self.steps) > 0:
            round += 1
            logger.info("Running round", round=round, steps_left=len(self.steps))

            steps_to_run = []
            for step in self.steps:
                if len(self.prevs[str(id(step))]) == 0:
                    steps_to_run.append(step)
                else:
                    break

            for idx, step in enumerate(steps_to_run):
                self.steps.popleft()

            tasks = [self._run_step(step, ctx) for step in steps_to_run]
            await asyncio.gather(*tasks)


def step(fn: Callable):
    _step = Step(fn)
    Step.step_bags[_step.fn_name] = _step

    return _step
