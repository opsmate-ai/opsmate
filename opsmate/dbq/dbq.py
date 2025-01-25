from typing import List, Any, Dict, Callable, Awaitable
from sqlmodel import Column, JSON
from enum import Enum
from datetime import datetime, UTC
from sqlmodel import Session, select, SQLModel, Field, update
import importlib
import asyncio
import structlog
import time

logger = structlog.get_logger(__name__)


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskItem(SQLModel, table=True):
    id: int = Field(primary_key=True)
    args: List[Any] = Field(sa_column=Column(JSON))
    kwargs: Dict[str, Any] = Field(sa_column=Column(JSON))
    func: str

    result: Any = Field(sa_column=Column(JSON))
    status: TaskStatus = Field(default=TaskStatus.PENDING)

    generation_id: int = Field(default=1)
    created_at: datetime = Field(default=datetime.now(UTC))
    updated_at: datetime = Field(default=datetime.now(UTC))


def enqueue_task(
    session: Session,
    fn: Callable[..., Awaitable[Any]],
    *args: List[Any],
    **kwargs: Dict[str, Any],
):
    fn_module = fn.__module__
    fn_name = fn.__name__

    task = TaskItem(
        func=f"{fn_module}.{fn_name}",
        args=args,
        kwargs=kwargs,
    )
    session.add(task)
    session.commit()

    return task.id


def dequeue_task(session: Session):
    task = session.exec(
        select(TaskItem).where(
            TaskItem.status == TaskStatus.PENDING,
        )
    ).first()

    if not task:
        return None

    # run the update statement
    result = session.exec(
        update(TaskItem)
        .where(TaskItem.id == task.id)
        .where(TaskItem.generation_id == task.generation_id)
        .values(
            status=TaskStatus.RUNNING,
            generation_id=task.generation_id + 1,
            updated_at=datetime.now(UTC),
        )
    )
    if result.rowcount == 0:
        return dequeue_task(session)

    session.refresh(task)
    return task


async def await_task_completion(
    session: Session,
    task_id: int,
    timeout: float = 5,
    interval: float = 0.1,
) -> TaskItem:
    start = time.time()
    while True:
        task = session.exec(select(TaskItem).where(TaskItem.id == task_id)).first()
        logger.info("task status", task_id=task_id, status=task.status)
        if task.status == TaskStatus.COMPLETED or task.status == TaskStatus.FAILED:
            return task
        if time.time() - start > timeout:
            raise TimeoutError(
                f"Task {task_id} did not complete within {timeout} seconds"
            )
        await asyncio.sleep(interval)


class Worker:
    def __init__(self, session: Session, concurrency: int = 1):
        self.session = session
        self.running = True
        self.lock = asyncio.Lock()
        self.concurrency = concurrency

    async def start(self):
        tasks = [self._start() for _ in range(self.concurrency)]
        await asyncio.gather(*tasks)

    async def _start(self):
        while True:
            async with self.lock:
                if not self.running:
                    break

            await self._run()

    async def _run(self):
        task = dequeue_task(self.session)

        if not task:
            await asyncio.sleep(0.1)
            return
        logger.info("dequeue task", task_id=task.id)
        try:
            logger.info("importing function", func=task.func)
            fn_module, fn_name = task.func.rsplit(".", 1)
            fn = getattr(importlib.import_module(fn_module), fn_name)
            logger.info("imported function", func=task.func)
            result = await fn(*task.args, **task.kwargs)

            logger.info("task completed", task_id=task.id, result=result)
            task.result = result
            task.status = TaskStatus.COMPLETED
            self.session.commit()
        except Exception as e:
            logger.error("error running task", error=e)
            task.result = str(e)
            task.status = TaskStatus.FAILED
            self.session.commit()
            return

    async def stop(self):
        async with self.lock:
            self.running = False


async def dummy(a, b):
    return a + b
