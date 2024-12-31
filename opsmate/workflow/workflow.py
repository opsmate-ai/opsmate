from typing import Callable, Any, Dict, Awaitable, List, Set, Optional
from enum import Enum
from collections import deque
import asyncio
import structlog
import uuid
from collections import defaultdict
from sqlmodel import Session
from .models import (
    Workflow,
    WorkflowStep,
    WorkflowType,
    WorkflowState,
    WorkflowFailedReason,
)
import pickle
import importlib
import traceback

logger = structlog.get_logger(__name__)


class WorkflowContext:
    def __init__(self, results: Dict[str, Any] = {}, input: Dict[str, Any] = {}):
        self.results = results
        self.input = input
        self._lock = asyncio.Lock()
        self.step_results = None

    async def set_result(self, key: str, value: Any):
        async with self._lock:
            self.results[key] = value

    def copy(self):
        return WorkflowContext(results=self.results.copy(), input=self.input.copy())

    def __repr__(self):
        return f"WorkflowContext({self.results})"


class Step:
    step_bags = {}

    def __init__(
        self,
        fn: Callable[[WorkflowContext], Awaitable[Any]] = None,
        op: WorkflowType = WorkflowType.NONE,
        steps: List["Step"] = [],
    ):
        self.id = str(uuid.uuid4()).split("-")[0]
        self.fn = fn
        self.fn_name = fn.__name__ if fn else None
        self.steps: List[Step] = steps
        self.prev = set(self.steps)
        self.op = op
        self.result = None

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

        right = right.copy()

        for step in right.__all_orphan_children():
            if seq_step not in step.prev:
                step.prev.add(seq_step)
                step.steps.append(seq_step)

        return right

    def copy(self):
        step = Step(
            fn=self.fn,
            op=self.op,
            steps=[child.copy() for child in self.steps],
        )
        step.id = self.id
        return step

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


def build_workflow(
    name: str, description: str, root: Step, session: Session
) -> Workflow:
    visisted = defaultdict(WorkflowStep)
    workflow = Workflow(name=name, description=description)
    session.add(workflow)
    session.commit()

    def _build(step: Step):
        step_id = str(id(step))
        if step_id in visisted:
            return visisted[step_id]

        child_workflow_steps = [_build(child) for child in step.steps]

        child_workflow_step_ids = [
            workflow_step.id for workflow_step in child_workflow_steps
        ]
        workflow_step = WorkflowStep(
            workflow_id=workflow.id,
            prev_ids=child_workflow_step_ids,
            name=step.fn_name,
            step_type=step.op,
        )
        if step.fn:
            workflow_step.fn = step.fn.__qualname__
        session.add(workflow_step)
        session.commit()
        visisted[step_id] = workflow_step
        return workflow_step

    _build(root)
    return workflow


class StatelessWorkflowExecutor:
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
                exec_ctx = ctx.copy()
                if len(step.steps) == 1:
                    exec_ctx.step_results = step.steps[0].result
                else:
                    exec_ctx.step_results = [child.result for child in step.steps]
                step.result = await step.fn(exec_ctx)
            elif step.op == WorkflowType.PARALLEL:
                step.result = [child.result for child in step.steps]

            elif step.op == WorkflowType.SEQUENTIAL:
                step.result = step.steps[0].result
            else:
                raise ValueError(f"Invalid step operation: {step.op}")

            async with self._lock:
                for rest_step in self.steps:
                    rest_step_id = str(id(rest_step))
                    if step in self.prevs[rest_step_id]:
                        self.prevs[rest_step_id].remove(step)

        await ctx.set_result(step.fn_name, step.result)
        return step.result

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


class WorkflowExecutor:
    def __init__(self, workflow: Workflow, session: Session, semerphore_size: int = 4):
        self.workflow = workflow
        self.session = session
        self.semerphore_size = semerphore_size
        self._semaphore = asyncio.Semaphore(semerphore_size)
        self._lock = asyncio.Lock()

    async def run(self, ctx: WorkflowContext = None):
        for hook in self.before_run_hooks:
            await hook(self)

        round = 0
        while not self._all_finished():
            round += 1
            logger.info("Running round", round=round)

            steps_to_run = self.workflow.runnable_steps(self.session)

            tasks = [self._run_step(step, ctx) for step in steps_to_run]
            await asyncio.gather(*tasks)

        for hook in self.after_run_hooks:
            await hook(self)

        self.session.refresh(self.workflow)

    async def mark_rerun(self, step: WorkflowStep):
        """
        Mark a workflow as pending and rerun it.
        A selected step will be re-marked as pending, so are its descendants.
        """
        self.workflow.state = WorkflowState.PENDING
        self.session.commit()

        nodes = {}
        edges = defaultdict(list)

        def build(node: WorkflowStep):
            node_id = node.id
            if node_id not in nodes:
                nodes[node_id] = node
                for child in node.prev_steps(self.session):
                    build(child)
                    edges[child.id].append(node_id)

        for s in self.workflow.steps:
            build(s)

        visited = set()

        def visit(node_id: int):
            if node_id in visited:
                return

            visited.add(node_id)
            node = nodes[node_id]
            node.state = WorkflowState.PENDING
            node.error = ""
            node.failed_reason = WorkflowFailedReason.NONE
            node.result = None
            self.session.commit()

            for next_node_id in edges[node_id]:
                visit(next_node_id)

        visit(step.id)

    async def _mark_workflow_running(self):
        self.workflow.state = WorkflowState.RUNNING
        self.session.commit()

    async def _mark_workflow_completed(self):
        if self.workflow.state == WorkflowState.FAILED:
            return
        self.workflow.state = WorkflowState.COMPLETED
        self.session.commit()

    async def _mark_workflow_failed(self, reason: WorkflowFailedReason):
        self.workflow.state = WorkflowState.FAILED
        self.session.commit()

    before_run_hooks = [
        _mark_workflow_running,
    ]

    after_run_hooks = [
        _mark_workflow_completed,
    ]

    after_step_failed_hooks = [
        _mark_workflow_failed,
    ]

    async def _run_step(self, step: WorkflowStep, ctx: WorkflowContext):
        if not await self._can_step_run(step):
            step.state = WorkflowState.FAILED
            step.failed_reason = WorkflowFailedReason.PREV_STEP_FAILED

            for hook in self.after_step_failed_hooks:
                await hook(self, step.failed_reason)

            self.session.commit()
            logger.error(
                "Step cannot run",
                step_id=step.id,
                step_name=step.name,
                failed_reason=step.failed_reason,
            )
            return

        async with self._semaphore:
            logger.info(
                "Running step",
                step_id=step.id,
                step_name=step.name,
                step_type=step.step_type,
            )
            step.state = WorkflowState.RUNNING
            self.session.commit()

            prev_steps = step.prev_steps(self.session)

            if step.step_type == WorkflowType.SEQUENTIAL:
                assert len(prev_steps) == 1
                prev_step = prev_steps[0]
                step.result = prev_step.result
                step.state = WorkflowState.COMPLETED
                self.session.commit()
                return

            if step.step_type == WorkflowType.PARALLEL:
                step.result = [prev_step.result for prev_step in prev_steps]
                step.state = WorkflowState.COMPLETED
                self.session.commit()
                return

            try:
                # xxx: this is a hack, need importlib instead of step_bags
                logger.info(
                    "Running step",
                    step_id=step.id,
                    step_name=step.name,
                    step_fn=step.fn,
                )
                func = Step.step_bags[step.name].fn
                exec_ctx = ctx.copy()

                if len(prev_steps) == 1:
                    exec_ctx.step_results = prev_steps[0].result
                else:
                    exec_ctx.step_results = [
                        prev_step.result for prev_step in prev_steps
                    ]
                step.result = await func(exec_ctx)

                step.state = WorkflowState.COMPLETED
                self.session.commit()
            except Exception as e:
                logger.error(
                    "Error running step",
                    step_id=step.id,
                    error=str(e),
                    stacktrace=traceback.format_exc(),
                )
                step.state = WorkflowState.FAILED
                step.failed_reason = WorkflowFailedReason.RUNTIME_ERROR
                step.error = str(e)
                self.session.commit()
                for hook in self.after_step_failed_hooks:
                    await hook(self, step.failed_reason)

    async def _can_step_run(self, step: WorkflowStep):
        """
        Check if previous steps are completed.
        If any of the previous steps has failed, return False.
        """
        prev_steps = step.prev_steps(self.session)
        for prev_step in prev_steps:
            if prev_step.state == WorkflowState.FAILED:
                return False
        return True

    def _all_finished(self):
        for step in self.workflow.steps:
            if (
                step.state != WorkflowState.COMPLETED
                and step.state != WorkflowState.FAILED
            ):
                return False
        return True
