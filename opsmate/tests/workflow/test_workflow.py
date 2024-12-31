import pytest
from opsmate.workflow import step
from opsmate.workflow.workflow import (
    Step,
    WorkflowType,
    StatelessWorkflowExecutor,
    WorkflowExecutor,
    WorkflowContext,
    WorkflowState,
    build_workflow,
    WorkflowFailedReason,
)
import asyncio
import structlog
from sqlmodel import Session, create_engine, SQLModel
from sqlalchemy import Engine

logger = structlog.get_logger(__name__)


@step
async def fn1(ctx):
    return "Hello"


@step
async def fn2(ctx):
    return "Hello"


@step
async def fn3(ctx):
    return "Hello"


@step
async def fn4(ctx):
    return "Hello"


@step
async def fn5(ctx):
    return "Hello"


@step
async def fn6(ctx):
    return "Hello"


@step
async def calc_fn1(ctx):
    assert ctx.step_results == []
    return 1


@step
async def calc_fn2(ctx):
    assert ctx.step_results == []
    return 2


@step
async def calc_fn3(ctx):
    childrens = ctx.step_results
    assert len(childrens) == 2
    assert childrens[0] == 1
    assert childrens[1] == 2
    return childrens[0] + childrens[1]


@step
async def calc_fn4(ctx):
    childrens = ctx.step_results
    assert len(childrens) == 2
    assert childrens[0] == 1
    assert childrens[1] == 2
    return childrens[0] * childrens[1]


@step
async def calc_fn5(ctx):
    childrens = ctx.step_results
    assert len(childrens) == 2
    assert childrens[0] == 3
    assert childrens[1] == 2
    return childrens[0] * childrens[1]


class TestWorkflow:

    @pytest.fixture
    def engine(self):
        engine = create_engine("sqlite:///:memory:")
        return engine

    @pytest.fixture
    def session(self, engine: Engine):
        SQLModel.metadata.create_all(engine)
        with Session(engine) as session:
            yield session

    def test_step_decorator(self):
        assert isinstance(fn1, Step)
        assert asyncio.iscoroutinefunction(fn1.fn)
        assert fn1.op == WorkflowType.NONE
        assert fn1.fn_name == "fn1"
        assert f"{fn1.fn_name}-{fn1.id}" in str(fn1)
        assert fn1.steps == []
        assert fn1.prev == set()

    def test_step_parallel(self):
        logger.info("testing the parallel workflow", format="fn1 | fn2 | fn3 | fn4")
        workflow = fn1 | fn2 | fn3 | fn4

        assert workflow.op == WorkflowType.PARALLEL
        assert workflow.steps == [fn1, fn2, fn3, fn4]
        assert workflow.prev == set([fn1, fn2, fn3, fn4])

        for fn in [fn1, fn2, fn3, fn4]:
            assert fn.prev == set()

        logger.info("testing the parallel workflow", format="(fn1 | fn2) | (fn3 | fn4)")
        workflow = (fn1 | fn2) | (fn3 | fn4)
        assert workflow.op == WorkflowType.PARALLEL
        assert workflow.steps == [fn1, fn2, fn3, fn4]
        assert workflow.prev == set([fn1, fn2, fn3, fn4])

        logger.info("testing the parallel workflow", format="fn1 | (fn2 | fn3) | fn4")
        workflow = fn1 | (fn2 | fn3) | fn4
        assert workflow.op == WorkflowType.PARALLEL
        assert workflow.steps == [fn1, fn2, fn3, fn4]
        assert workflow.prev == set([fn1, fn2, fn3, fn4])

        logger.info("testing the parallel workflow", format="fn1 | fn2 | (fn3 | fn4)")
        workflow = fn1 | fn2 | (fn3 | fn4)
        assert workflow.op == WorkflowType.PARALLEL
        assert workflow.steps == [fn1, fn2, fn3, fn4]
        assert workflow.prev == set([fn1, fn2, fn3, fn4])

    def test_step_sequential(self):
        logger.info("testing simple sequential workflow", format="fn1 >> fn2")

        result = fn1 >> fn2
        assert str(result) == str(fn2)
        assert len(result.prev) == 1
        assert len(result.steps) == 1

        seq_step = result.steps[0]
        assert seq_step in result.prev
        assert seq_step.fn is None
        assert seq_step.op == WorkflowType.SEQUENTIAL

        assert len(seq_step.steps) == 1
        assert len(seq_step.prev) == 1

        assert str(seq_step.steps[0]) == str(fn1)
        assert fn1 in seq_step.prev

        # make sure that the original functions are not modified
        for fn in [fn1, fn2]:
            assert len(fn.prev) == 0
            assert len(fn.steps) == 0

        logger.info("testing sequential workflow", format="fn1 >> (fn2 | fn3)")
        result = fn1 >> (fn2 | fn3)
        assert result.op == WorkflowType.PARALLEL
        assert len(result.steps) == 2
        wf_fn2 = self.can_find_fn_from_workflow(fn2, result)
        wf_fn3 = self.can_find_fn_from_workflow(fn3, result)

        assert len(wf_fn2.prev) == 1
        assert len(wf_fn3.prev) == 1
        assert len(wf_fn2.steps) == 1
        assert len(wf_fn3.steps) == 1
        assert wf_fn2.steps[0] == wf_fn3.steps[0]
        seq_step = wf_fn2.steps[0]
        assert seq_step.op == WorkflowType.SEQUENTIAL
        assert len(seq_step.steps) == 1
        assert len(seq_step.prev) == 1
        assert seq_step.steps[0] == fn1
        assert seq_step.prev == set([fn1])

        for fn in [fn1, fn2, fn3]:
            assert len(fn.prev) == 0, f"{fn.fn_name} should not have any prev"
            assert len(fn.steps) == 0, f"{fn.fn_name} should not have any steps"

    def can_find_fn_from_workflow(
        self,
        fn: Step,
        workflow: Step,
    ):
        for step in workflow.steps:
            if str(step) == str(fn):
                return step
        assert False, f"Function {fn} not found in workflow {workflow}"

    def test_topological_sort(self):
        workflow = fn1 >> fn2 >> fn3
        sorted = workflow.topological_sort()
        self.assert_topological_order(sorted, [fn1, fn2, fn3])

        workflow = (fn1 | fn2) >> (fn3 | fn4)
        sorted = workflow.topological_sort()
        self.assert_topological_order(sorted, [fn1, fn3])
        self.assert_topological_order(sorted, [fn1, fn4])
        self.assert_topological_order(sorted, [fn2, fn3])
        self.assert_topological_order(sorted, [fn2, fn4])

        workflow = fn1 >> (fn2 | fn3) >> fn4
        sorted = workflow.topological_sort()
        self.assert_topological_order(sorted, [fn1, fn2])
        self.assert_topological_order(sorted, [fn1, fn3])
        self.assert_topological_order(sorted, [fn2, fn4])
        self.assert_topological_order(sorted, [fn3, fn4])

        workflow = (fn1 | fn2) >> (fn3 | (fn4 >> fn5)) | fn6
        sorted = workflow.topological_sort()
        first_tier = [fn1, fn2, fn6]
        second_tier = [fn3, fn4, fn5]

        for first in first_tier:
            for second in second_tier:
                self.assert_topological_order(sorted, [first, second])

        self.assert_topological_order(sorted, [fn4, fn5])

    def assert_topological_order(self, result, expected):
        def find_id(step: Step):
            for idx, fn in enumerate(result):
                if str(fn) == str(step):
                    return idx
            return -1

        for f1, f2 in zip(expected, expected[1:]):
            assert find_id(f1) <= find_id(f2), f"{f1} should be before {f2}"

    @pytest.mark.asyncio
    async def test_workflow_run(self):
        @step
        async def fn1(ctx):
            return 1

        @step
        async def fn2(ctx):
            return 1

        @step
        async def fn3(ctx):
            return ctx.results["fn1"] + ctx.results["fn2"]

        steps = (fn1 | fn2) >> fn3
        workflow = StatelessWorkflowExecutor(steps)
        ctx = WorkflowContext()
        await workflow.run(ctx)
        assert ctx.results["fn3"] == 2

    @pytest.mark.asyncio
    async def test_workflow_run_using_result(self):
        steps = (calc_fn1 | calc_fn2) >> (calc_fn3 | calc_fn4) >> calc_fn5
        workflow = StatelessWorkflowExecutor(steps)
        ctx = WorkflowContext()
        await workflow.run(ctx)
        assert ctx.results["calc_fn3"] == 3
        assert ctx.results["calc_fn4"] == 2
        assert ctx.results["calc_fn5"] == 6

    def test_workflow_build(self, session):
        step = (calc_fn1 | calc_fn2) >> (calc_fn3 | calc_fn4) >> calc_fn5
        workflow = build_workflow("test", "test", step, session)

        assert workflow.id is not None
        assert workflow.name == "test"
        assert workflow.description == "test"
        assert workflow.steps is not None
        assert len(workflow.steps) == 9

        unsorted_steps = [step for step in workflow.steps]

        for workflow_step in workflow.steps:
            assert workflow_step.created_at is not None
            assert workflow_step.updated_at is not None

        assert workflow.state == WorkflowState.PENDING

        steps = workflow.topological_sort(session)

        for idx, step in enumerate(steps):
            prev_step_ids = [step.id for step in steps[:idx]]
            for prev_step in step.prev_steps(session):
                assert prev_step.id in prev_step_ids

    @pytest.mark.asyncio
    async def test_stateful_workflow_run(self, session):
        step = (calc_fn1 | calc_fn2) >> (calc_fn3 | calc_fn4) >> calc_fn5
        workflow = build_workflow("test", "test", step, session)

        workflow_executor = WorkflowExecutor(workflow, session)
        await workflow_executor.run(WorkflowContext())

        f5_step = workflow.find_step("calc_fn5", session)
        assert f5_step is not None
        assert f5_step.result is not None
        assert f5_step.result == 6

        f4_step = workflow.find_step("calc_fn4", session)
        assert f4_step is not None
        assert f4_step.result is not None
        assert f4_step.result == 2

        f3_step = workflow.find_step("calc_fn3", session)
        assert f3_step is not None
        assert f3_step.result is not None
        assert f3_step.result == 3

        f2_step = workflow.find_step("calc_fn2", session)
        assert f2_step is not None
        assert f2_step.result is not None
        assert f2_step.result == 2

        f1_step = workflow.find_step("calc_fn1", session)
        assert f1_step is not None
        assert f1_step.result is not None
        assert f1_step.result == 1

        session.refresh(workflow)
        assert workflow.state == WorkflowState.COMPLETED

    @pytest.mark.asyncio
    async def test_workflow_run_with_hooks(self, session):
        @step
        async def test_hook1(ctx):
            return 1

        @step
        async def test_hook2(ctx):
            raise ValueError("just failed")

        @step
        async def test_hook3(ctx):
            return 3

        @step
        async def test_hook4(ctx):
            return 4

        blueprint = test_hook1 >> (test_hook2 | test_hook3) >> test_hook4
        workflow = build_workflow("test", "test", blueprint, session)
        workflow_executor = WorkflowExecutor(workflow, session)
        await workflow_executor.run(WorkflowContext())

        assert workflow.state == WorkflowState.FAILED

        print("*" * 100)
        print(workflow.steps)
        print("*" * 100)
        hook1 = workflow.find_step("test_hook1", session)
        assert hook1 is not None
        assert hook1.failed_reason == WorkflowFailedReason.NONE

        hook2 = workflow.find_step("test_hook2", session)
        assert hook2 is not None
        assert hook2.failed_reason == WorkflowFailedReason.RUNTIME_ERROR

        hook3 = workflow.find_step("test_hook3", session)
        assert hook3 is not None
        assert hook3.result == 3
        assert hook3.failed_reason == WorkflowFailedReason.NONE

        hook4 = workflow.find_step("test_hook4", session)
        assert hook4 is not None
        assert hook4.failed_reason == WorkflowFailedReason.PREV_STEP_FAILED
