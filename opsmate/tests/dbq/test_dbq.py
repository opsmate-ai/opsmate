import pytest
from sqlmodel import Session, create_engine, select
from sqlalchemy import Engine
from opsmate.dbq.dbq import (
    SQLModel,
    enqueue_task,
    dequeue_task,
    TaskItem,
    TaskStatus,
    Worker,
    await_task_completion,
    dbq_task,
    Task,
    purge_tasks,
)
import asyncio
import structlog
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, UTC
import random

logger = structlog.get_logger(__name__)


async def dummy(a, b):
    return a + b


@dbq_task(
    retry_on=(TypeError,),
    max_retries=1,
)
async def dummy_with_retry_on(a, b):
    raise a + b


@dbq_task(
    max_retries=1,
    back_off_func=lambda retry_count: (
        # exponential backoff
        datetime.now(UTC)
        + timedelta(milliseconds=1 ** (retry_count - 1) + random.uniform(0, 0.1))
    ),
    priority=10,
)
async def dummy_plus(a: int, b: int):
    return a + b


async def dummy_with_complex_signature(a: int, b: int, c: dict, d: int = 1):
    return a + b + c["a"] + d


async def dummy_return_complex_value():
    return {"a": 1, "b": 2}


async def dummy_with_context(ctx: dict):
    session: Session = ctx["session"]
    # execute select 1
    result = session.exec(select(1)).first()
    return result


class DummyTask(Task):
    async def before_run(self, task_item: TaskItem, ctx: dict):
        session: Session = ctx["session"]
        task_item.args = [1, 2]
        session.add(task_item)
        session.commit()

    async def on_success(self, task_item: TaskItem, ctx: dict):
        session: Session = ctx["session"]
        task_item.result += 1
        session.add(task_item)
        session.commit()


@dbq_task(
    max_retries=1,
    back_off_func=lambda retry_count: (
        # exponential backoff
        datetime.now(UTC)
        + timedelta(milliseconds=1 ** (retry_count - 1) + random.uniform(0, 0.1))
    ),
    task_type=DummyTask,
)
async def custom_dummy_task(a: int, b: int):
    return a + b


class TestDbq:
    @pytest.fixture
    def engine(self):
        engine = create_engine("sqlite:///:memory:")
        SQLModel.metadata.create_all(engine)
        return engine

    @pytest.fixture
    def session(self, engine: Engine):
        with Session(engine) as session:
            yield session

    @asynccontextmanager
    async def with_worker(self, engine: Engine):
        worker = Worker(engine, concurrency=2)
        worker_task = asyncio.create_task(worker.start())
        try:
            yield worker
        finally:
            await worker.stop()
            worker_task.cancel()
            try:
                await worker_task
            except asyncio.CancelledError:
                logger.info("worker task cancelled")

    def test_enqueue_task(self, session: Session):
        task_id = enqueue_task(session, dummy, 1, 2)

        task = session.exec(select(TaskItem).where(TaskItem.id == task_id)).first()
        assert task is not None
        assert task.args == [1, 2]
        assert task.kwargs == {}
        assert task.status == TaskStatus.PENDING
        assert task.func == "test_dbq.dummy"
        assert task.created_at is not None
        assert task.updated_at is not None
        assert task.generation_id == 1

    def test_dequeue_task(self, session: Session):
        task_id = enqueue_task(session, dummy, 1, 2)
        task = dequeue_task(session)

        assert task is not None
        assert task.id == task_id
        assert task.args == [1, 2]
        assert task.kwargs == {}
        assert task.status == TaskStatus.RUNNING
        assert task.generation_id == 2

    @pytest.mark.asyncio
    async def test_worker(self, session: Session, engine: Engine):
        async with self.with_worker(engine):
            task_id = enqueue_task(session, dummy, 1, 2)
            task = await await_task_completion(session, task_id, 3)
            assert task.result == 3

    @pytest.mark.asyncio
    async def test_worker_with_concurrency(self, session: Session, engine: Engine):
        async with self.with_worker(engine):
            task_id = enqueue_task(session, dummy, 1, 2)
            task_id2 = enqueue_task(session, dummy, 2, 3)
            task = await await_task_completion(session, task_id, 3)
            assert task.result == 3
            task2 = await await_task_completion(session, task_id2, 3)
            assert task2.result == 5

    @pytest.mark.asyncio
    async def test_worker_with_exception_without_retry(
        self, session: Session, engine: Engine
    ):
        async with self.with_worker(engine):
            task_id = enqueue_task(session, dummy, 1, "abc")
            task = await await_task_completion(session, task_id, 3)
            assert task.result is None
            assert task.status == TaskStatus.FAILED
            assert task.error.startswith(
                "unsupported operand type(s) for +: 'int' and 'str'"
            )
            assert task.wait_until is not None
            assert task.max_retries == 3
            assert (
                task.retry_count == 0
            ), "should not retry as the error is not in the retry on list"

    @pytest.mark.asyncio
    async def test_worker_with_exception_with_retry(
        self, session: Session, engine: Engine
    ):
        async with self.with_worker(engine):
            task_id = enqueue_task(session, dummy_with_retry_on, 1, "a")
            task = await await_task_completion(session, task_id, 3)
            assert task.result is None
            assert task.status == TaskStatus.FAILED
            assert task.retry_count == 1
            assert task.error.startswith(
                "unsupported operand type(s) for +: 'int' and 'str'"
            )
            assert task.wait_until is not None
            assert task.max_retries == 1

    @pytest.mark.asyncio
    async def test_task_with_decorator_max_retries(
        self, session: Session, engine: Engine
    ):
        async with self.with_worker(engine):
            task_id = enqueue_task(session, dummy_plus, 1, "a")
            task = await await_task_completion(session, task_id, 3)
            assert task.result == None
            assert task.status == TaskStatus.FAILED
            assert task.error.startswith(
                "unsupported operand type(s) for +: 'int' and 'str'"
            )
            assert task.retry_count == 1
            assert task.wait_until is not None
            assert task.max_retries == 1

    @pytest.mark.asyncio
    async def test_task_with_complex_signature(self, session: Session, engine: Engine):
        async with self.with_worker(engine):
            task_id = enqueue_task(
                session,
                dummy_with_complex_signature,
                1,
                2,
                c={"a": 1},
            )
            task = await await_task_completion(session, task_id, 3)
            assert task.result == 5
            assert task.status == TaskStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_task_with_complex_return_value(
        self, session: Session, engine: Engine
    ):
        async with self.with_worker(engine):
            task_id = enqueue_task(session, dummy_return_complex_value)
            task = await await_task_completion(session, task_id, 3)
            assert task.result == {"a": 1, "b": 2}
            assert task.status == TaskStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_worker_queue_size(self, session: Session, engine: Engine):
        worker = Worker(engine, concurrency=2)
        assert worker.queue_size() == 0
        enqueue_task(session, dummy, 1, 2)
        assert worker.queue_size() == 1

    @pytest.mark.asyncio
    async def test_worker_inflight_size(self, session: Session, engine: Engine):
        worker = Worker(engine, concurrency=2)
        assert worker.inflight_size() == 0
        task_id = enqueue_task(session, dummy, 1, 2)
        task = session.exec(select(TaskItem).where(TaskItem.id == task_id)).first()
        task.status = TaskStatus.RUNNING
        session.commit()

        assert worker.inflight_size() == 1

    @pytest.mark.asyncio
    async def test_task_with_priority(self, session: Session, engine: Engine):
        task_id = enqueue_task(session, dummy, 1, 2, priority=1)
        task_id2 = enqueue_task(session, dummy, 1, 2, priority=2)
        async with self.with_worker(engine):
            task = await await_task_completion(session, task_id, 3)
            assert task.result == 3
            task2 = await await_task_completion(session, task_id2, 3)
            assert task2.result == 3

            assert task.updated_at > task2.updated_at

    @pytest.mark.asyncio
    async def test_task_with_decorator_with_priority(
        self, session: Session, engine: Engine
    ):
        async with self.with_worker(engine):
            task_id = enqueue_task(session, dummy_plus, 1, 2)
            task = await await_task_completion(session, task_id, 3)
            assert task.result == 3

            task_id2 = enqueue_task(session, dummy_plus, 1, 2, priority=2)
            task2 = await await_task_completion(session, task_id2, 3)
            assert task2.result == 3

            assert task.updated_at < task2.updated_at

    @pytest.mark.asyncio
    async def test_task_with_custom_task(self, session: Session, engine: Engine):
        async with self.with_worker(engine):
            task_id = enqueue_task(session, custom_dummy_task, 4, 5)
            task = await await_task_completion(session, task_id, 3)
            assert task.result == 4
            assert task.args == [1, 2]
            assert task.status == TaskStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_task_with_context(self, session: Session, engine: Engine):
        async with self.with_worker(engine):
            task_id = enqueue_task(session, dummy_with_context)
            task = await await_task_completion(session, task_id, 3)
            assert task.result == 1

    def test_purge_tasks(self, session: Session, engine: Engine):
        # Create tasks with different statuses
        task_id1 = enqueue_task(session, dummy, 1, 2)
        task_id2 = enqueue_task(session, dummy, 3, 4)
        task_id3 = enqueue_task(session, dummy_plus, 5, 6)
        enqueue_task(session, dummy_plus, 7, 8)
        enqueue_task(session, dummy_with_context)

        # Set different statuses
        task1 = session.exec(select(TaskItem).where(TaskItem.id == task_id1)).first()
        task1.status = TaskStatus.RUNNING

        task2 = session.exec(select(TaskItem).where(TaskItem.id == task_id2)).first()
        task2.status = TaskStatus.COMPLETED

        task3 = session.exec(select(TaskItem).where(TaskItem.id == task_id3)).first()
        task3.status = TaskStatus.FAILED

        session.commit()

        # Test purging only non-running tasks for dummy function
        purged_count, running_count = purge_tasks(
            session, "test_dbq.dummy", non_running=True
        )
        assert purged_count == 1, "Should purge one non-running dummy task"
        assert running_count == 1, "Should have one running dummy task"

        # Verify remaining tasks
        remaining_tasks = session.exec(select(TaskItem)).all()
        assert len(remaining_tasks) == 4, "Should have 4 tasks remaining"

        # Test purging all tasks for dummy_plus function
        purged_count, running_count = purge_tasks(
            session, "test_dbq.dummy_plus", non_running=False
        )
        assert purged_count == 2, "Should purge all dummy_plus tasks"
        assert running_count == 0, "Should have no running dummy_plus tasks"

        # Verify remaining tasks
        remaining_tasks = session.exec(select(TaskItem)).all()
        assert len(remaining_tasks) == 2, "Should have 2 tasks remaining"

        # Test purging with custom queue name
        task_id6 = enqueue_task(session, dummy, 9, 10, queue_name="custom_queue")
        purged_count, running_count = purge_tasks(
            session, "test_dbq.dummy", queue_name="custom_queue"
        )
        assert purged_count == 1, "Should purge task from custom queue"
        assert running_count == 0, "Should have no running tasks in custom queue"

        # Test purging running tasks
        purged_count, running_count = purge_tasks(
            session, "test_dbq.dummy", non_running=False
        )
        assert purged_count == 1, "Should purge remaining dummy task (running)"
        assert running_count == 0, "Should have no running dummy tasks remaining"

        # Verify final state
        remaining_tasks = session.exec(select(TaskItem)).all()
        assert len(remaining_tasks) == 1, "Should have 1 task remaining"
        assert remaining_tasks[0].func == "test_dbq.dummy_with_context"
