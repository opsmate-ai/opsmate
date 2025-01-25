import pytest
from sqlmodel import Session, create_engine, select
from sqlalchemy import Engine
from opsmate.dbq.dbq import (
    SQLModel,
    enqueue_task,
    dequeue_task,
    TaskItem,
    TaskStatus,
    dummy,
    Worker,
    await_task_completion,
)
import asyncio
import structlog
from contextlib import asynccontextmanager

logger = structlog.get_logger(__name__)


async def dummy_with_complex_signature(a: int, b: int, c: dict, d: int = 1):
    return a + b + c["a"] + d


async def dummy_return_complex_value():
    return {"a": 1, "b": 2}


class TestDbq:
    @pytest.fixture
    def engine(self):
        engine = create_engine("sqlite:///:memory:")
        return engine

    @pytest.fixture
    def session(self, engine: Engine):
        SQLModel.metadata.create_all(engine)
        with Session(engine) as session:
            yield session

    @asynccontextmanager
    async def with_worker(self, session: Session):
        worker = Worker(session, concurrency=2)
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
        assert task.func == "opsmate.dbq.dbq.dummy"
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
    async def test_worker(self, session: Session):
        async with self.with_worker(session):
            task_id = enqueue_task(session, dummy, 1, 2)
            task = await await_task_completion(session, task_id, 3)
            assert task.result == 3

    @pytest.mark.asyncio
    async def test_worker_with_concurrency(self, session: Session):
        async with self.with_worker(session):
            task_id = enqueue_task(session, dummy, 1, 2)
            task_id2 = enqueue_task(session, dummy, 2, 3)
            task = await await_task_completion(session, task_id, 3)
            assert task.result == 3
            task2 = await await_task_completion(session, task_id2, 3)
            assert task2.result == 5

    @pytest.mark.asyncio
    async def test_worker_with_exception(self, session: Session):
        async with self.with_worker(session):
            task_id = enqueue_task(session, dummy, 1, "abc")
            task = await await_task_completion(session, task_id, 3)
            assert task.result is None
            assert task.status == TaskStatus.FAILED
            assert task.error.startswith(
                "unsupported operand type(s) for +: 'int' and 'str'"
            )

    @pytest.mark.asyncio
    async def test_task_with_complex_signature(self, session: Session):
        async with self.with_worker(session):
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
    async def test_task_with_complex_return_value(self, session: Session):
        async with self.with_worker(session):
            task_id = enqueue_task(session, dummy_return_complex_value)
            task = await await_task_completion(session, task_id, 3)
            assert task.result == {"a": 1, "b": 2}
            assert task.status == TaskStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_task_with_priority(self, session: Session):
        task_id = enqueue_task(session, dummy, 1, 2, priority=1)
        task_id2 = enqueue_task(session, dummy, 1, 2, priority=2)
        async with self.with_worker(session):
            task = await await_task_completion(session, task_id, 3)
            assert task.result == 3
            task2 = await await_task_completion(session, task_id2, 3)
            assert task2.result == 3

            assert task.updated_at > task2.updated_at
