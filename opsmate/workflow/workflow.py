from typing import Callable, Any, Dict, Awaitable, List, Optional
from collections import deque
import asyncio
import structlog
import uuid
from collections import defaultdict
from sqlmodel import Session, select
from .models import (
    Workflow,
    WorkflowStep,
    WorkflowType,
    WorkflowState,
    WorkflowFailedReason,
)
import traceback
from functools import reduce

logger = structlog.get_logger(__name__)


class WorkflowContext:
    def __init__(
        self,
        results: Dict[str, Any] = {},
        input: Dict[str, Any] = {},
        metadata: Dict[str, Any] = {},
    ):
        self.results = results
        self.input = input
        self.metadata = metadata
        self._lock = asyncio.Lock()
        self.step_results = None

    async def set_result(self, key: str, value: Any):
        async with self._lock:
            self.results[key] = value

    def copy(self):
        return WorkflowContext(
            results=self.results.copy(),
            input=self.input.copy(),
            metadata=self.metadata.copy(),
        )

    def find_result(self, step_name: str, session: Session):
        if self.step_id == None or self.workflow_id == None:
            raise ValueError("step_id and workflow_id must be set")

        stmt = (
            select(WorkflowStep)
            .where(WorkflowStep.workflow_id == self.workflow_id)
            .where(WorkflowStep.name == step_name)
        )
        workflow_step = session.exec(stmt).first()
        if workflow_step is None:
            raise ValueError(f"Workflow step {step_name} not found")
        return workflow_step.result

    def step(self, session: Session):
        if self.step_id == None or self.workflow_id == None:
            raise ValueError("step_id and workflow_id must be set")

        stmt = (
            select(WorkflowStep)
            .where(WorkflowStep.id == self.step_id)
            .where(WorkflowStep.workflow_id == self.workflow_id)
        )

        workflow_step = session.exec(stmt).first()
        if workflow_step is None:
            raise ValueError(f"Workflow step {self.step_id} not found")
        return workflow_step

    def __repr__(self):
        return f"WorkflowContext({self.results})"


class Step:
    step_bags = {}

    def __init__(
        self,
        fn: Callable[[WorkflowContext], Awaitable[Any]] = None,
        op: WorkflowType = WorkflowType.NONE,
        steps: List["Step"] = [],
        skip_exec: bool = False,
        metadata: Dict[str, Any] = {},
        pre_run_hooks: List[Callable[[WorkflowContext], Awaitable[Any]]] = [],
        post_success_hooks: List[Callable[[WorkflowContext, Any], Awaitable[Any]]] = [],
        post_failure_hooks: List[
            Callable[[WorkflowContext, Exception], Awaitable[Any]]
        ] = [],
    ):
        self.id = str(uuid.uuid4()).split("-")[0]
        self.fn = fn
        self.fn_name = fn.__name__ if fn else None
        self.steps: List[Step] = steps
        self.prev = set(self.steps)
        self.op = op
        self.result = None
        self.skip_exec = skip_exec
        self.metadata = metadata
        self.pre_run_hooks = pre_run_hooks
        self.post_success_hooks = post_success_hooks
        self.post_failure_hooks = post_failure_hooks

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

        logger.info("rshift", left=self, right=right)

        orphans = right.all_orphan_children()
        right = right.copy()

        orphans = right.all_orphan_children()
        for step in orphans:
            if seq_step not in step.prev:
                step.prev.add(seq_step)
                step.steps.append(seq_step)
        return right

    def copy(self):
        visisted = {}

        def _copy(step: Step):
            if str(id(step)) in visisted:
                return visisted[str(id(step))]

            copied_step = Step(
                fn=step.fn,
                op=step.op,
                steps=[_copy(child) for child in step.steps],
                metadata=step.metadata.copy(),
                pre_run_hooks=step.pre_run_hooks.copy(),
                post_success_hooks=step.post_success_hooks.copy(),
                post_failure_hooks=step.post_failure_hooks.copy(),
            )
            visisted[str(id(step))] = copied_step
            copied_step.id = step.id
            return copied_step

        return _copy(self)

    def all_orphan_children(self):
        results = set()

        def find(step: Step):
            if (
                step.op == WorkflowType.NONE
                or step.op == WorkflowType.COND_TRUE
                or step.op == WorkflowType.COND_FALSE
            ) and step.steps == []:
                results.add(step)
            else:
                for child in step.steps:
                    find(child)

        find(self)
        return list(results)

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
        workflow_step.meta = step.metadata
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
            for child in step.steps:
                if child.skip_exec:
                    step.skip_exec = True
                    break

            if step.op == WorkflowType.NONE:
                exec_ctx = ctx.copy()
                if len(step.steps) == 1:
                    exec_ctx.step_results = step.steps[0].result
                else:
                    exec_ctx.step_results = [child.result for child in step.steps]
                exec_ctx.metadata = step.metadata

                for hook in step.pre_run_hooks:
                    logger.info("Running pre run hook", hook=hook)
                    await hook(exec_ctx)

                try:
                    step.result = await step.fn(exec_ctx)
                    for hook in step.post_success_hooks:
                        await hook(exec_ctx, step.result)
                except Exception as e:
                    for hook in step.post_failure_hooks:
                        await hook(exec_ctx, e)
            elif (
                step.op == WorkflowType.COND_TRUE or step.op == WorkflowType.COND_FALSE
            ):
                exec_ctx = ctx.copy()
                assert len(step.steps) == 1
                exec_ctx.step_results = step.steps[0].result
                step.result = await step.fn(exec_ctx)
                if not step.result and WorkflowType.COND_TRUE == step.op:
                    step.skip_exec = True
                elif not step.result and WorkflowType.COND_FALSE == step.op:
                    step.skip_exec = True

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


def step(
    *args,
    op: WorkflowType = WorkflowType.NONE,
    pre_run_hooks: List[Callable[[WorkflowContext], Awaitable[Any]]] = [],
    post_success_hooks: List[Callable[[WorkflowContext, Any], Awaitable[Any]]] = [],
    post_failure_hooks: List[
        Callable[[WorkflowContext, Exception], Awaitable[Any]]
    ] = [],
):
    """
    Decorator to define a step in a workflow.

    Example:

    @step
    async def my_step(ctx: WorkflowContext):
        pass

    @step(WorkflowType.PARALLEL)
    async def my_parallel_step(ctx: WorkflowContext):
        pass

    @step(WorkflowType.None)
    async def my_none_step(ctx: WorkflowContext):
    """
    if len(args) == 1:
        arg0 = args[0]
        if asyncio.iscoroutinefunction(arg0):
            fn = arg0
            _step = Step(fn, WorkflowType.NONE)
            Step.step_bags[_step.fn_name] = _step
            return _step
        else:
            raise ValueError("The function must be a coroutine function")

    def wrapper(fn: Callable):
        _step = Step(
            fn,
            op,
            pre_run_hooks=pre_run_hooks,
            post_success_hooks=post_success_hooks,
            post_failure_hooks=post_failure_hooks,
        )
        Step.step_bags[_step.fn_name] = _step
        return _step

    return wrapper


def step_factory(step: Step):
    if len(step.steps) != 0:
        raise ValueError("step_factory can only be used on steps with no children")

    def wrapper(metadata: Dict[str, Any] = {}):
        return Step(fn=step.fn, op=step.op, metadata=metadata)

    return wrapper


# xxx: side effect appears to be a problem thus commented out for now
# def pre_run_hook(s: Step):
#     def wrapper(fn: Callable):
#         logger.info("Adding pre run hook", fn=fn, step=s)
#         step = s.copy()
#         step.pre_run_hooks.append(fn)
#         Step.step_bags[step.fn_name] = step
#         return step

#     return wrapper


# def post_success_hook(s: Step):
#     def wrapper(fn: Callable):
#         logger.info("Adding post success hook", fn=fn, step=s)
#         step = s.copy()
#         step.post_success_hooks.append(fn)
#         return step

#     return wrapper


# def post_failure_hook(s: Step):
#     def wrapper(fn: Callable):
#         logger.info("Adding post failure hook", fn=fn, step=s)
#         step = s.copy()
#         step.post_failure_hooks.append(fn)
#         return step

#     return wrapper


@step(op=WorkflowType.COND_TRUE)
async def _cond_true(ctx: WorkflowContext):
    if isinstance(ctx.step_results, list):
        assert len(ctx.step_results) == 1
        prev_result = ctx.step_results[0]
    else:
        prev_result = ctx.step_results
    return prev_result


@step(op=WorkflowType.COND_FALSE)
async def _cond_false(ctx: WorkflowContext):
    if isinstance(ctx.step_results, list):
        assert len(ctx.step_results) == 1
        prev_result = ctx.step_results[0]
    else:
        prev_result = ctx.step_results
    return not prev_result


def cond(condition: Step, left: Optional[Step] = None, right: Optional[Step] = None):
    """
    params:
        condition: a step that returns a boolean
        left: a step to run if the condition is true
        right: a step to run if the condition is false
    """
    if left is None and right is None:
        raise ValueError("Either left or right must be provided")

    conds = []
    if left:
        conds.append(_cond_true >> left)
    if right:
        conds.append(_cond_false >> right)

    conds = reduce(lambda x, y: x | y, conds)

    return condition >> conds


class WorkflowExecutor:
    def __init__(self, workflow: Workflow, session: Session, semerphore_size: int = 4):
        self.workflow = workflow
        self.session = session
        self.semerphore_size = semerphore_size
        self._semaphore = asyncio.Semaphore(semerphore_size)
        self._lock = asyncio.Lock()

    async def run(self, ctx: WorkflowContext = None, max_rounds: int = 100):
        for hook in self.before_run_hooks:
            await hook(self)

        round = 0
        while not self._all_finished() and round < max_rounds:
            round += 1
            logger.info("Running round", round=round)

            steps_to_run = self.workflow.runnable_steps(self.session)

            tasks = [self._run_step(step, ctx) for step in steps_to_run]
            await asyncio.gather(*tasks)

        for hook in self.after_run_hooks:
            await hook(self)

        self.session.refresh(self.workflow)

    async def mark_rerun(self, step: WorkflowStep, self_rerun: bool = True):
        """
        Marks:
        - a workflow and its descendants as pending if `self_rerun` is True
        - or the descendants of the selected step as pending if `self_rerun` is False
        """
        if self_rerun:
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
            if self_rerun or node.id != step.id:
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
        logger.info("Running step", step_id=step.id, step_name=step.name)
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

            for prev_step in prev_steps:
                if prev_step.state == WorkflowState.SKIPPED:
                    step.state = WorkflowState.SKIPPED
                    step.result = None
                    self.session.commit()
                    return

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

            if (
                step.step_type == WorkflowType.COND_TRUE
                or step.step_type == WorkflowType.COND_FALSE
            ):
                assert len(prev_steps) == 1
                prev_step = prev_steps[0]
                exec_ctx = ctx.copy()
                exec_ctx.step_results = prev_step.result
                exec_ctx.step_id = step.id
                exec_ctx.workflow_id = step.workflow_id
                step_definition = Step.step_bags[step.name]
                func = step_definition.fn

                for hook in step_definition.pre_run_hooks:
                    logger.info("Running pre run hook", hook=hook)
                    await hook(exec_ctx)

                self.session.refresh(step)

                if step.state != WorkflowState.SKIPPED:
                    step.result = await func(exec_ctx)

                for hook in step_definition.post_success_hooks:
                    await hook(exec_ctx, step.result)

                if not step.result and step.step_type == WorkflowType.COND_TRUE:
                    step.state = WorkflowState.SKIPPED
                elif not step.result and step.step_type == WorkflowType.COND_FALSE:
                    step.state = WorkflowState.SKIPPED
                elif step.state != WorkflowState.SKIPPED:
                    step.state = WorkflowState.COMPLETED

                logger.info(
                    "Step completed",
                    step_id=step.id,
                    step_name=step.name,
                    step_state=step.state,
                )
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
                step_definition = Step.step_bags[step.name]
                func = step_definition.fn
                exec_ctx = ctx.copy()

                if len(prev_steps) == 1:
                    exec_ctx.step_results = prev_steps[0].result
                else:
                    exec_ctx.step_results = [
                        prev_step.result for prev_step in prev_steps
                    ]
                exec_ctx.step_id = step.id
                exec_ctx.workflow_id = step.workflow_id
                exec_ctx.metadata = step.meta

                for hook in step_definition.pre_run_hooks:
                    logger.info("Running pre run hook", hook=hook)
                    await hook(exec_ctx)

                self.session.refresh(step)
                if step.state != WorkflowState.SKIPPED:
                    step.result = await func(exec_ctx)
                else:
                    step.result = None

                for hook in step_definition.post_success_hooks:
                    logger.info("Running post success hook", hook=hook)
                    await hook(exec_ctx, step.result)

                if step.state != WorkflowState.SKIPPED:
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
                for hook in step_definition.post_failure_hooks:
                    await hook(exec_ctx, e)

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
                and step.state != WorkflowState.SKIPPED
            ):
                return False
        return True
