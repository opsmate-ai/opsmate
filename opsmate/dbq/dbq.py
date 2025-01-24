from typing import List, Any, Dict, Callable, Awaitable
from sqlmodel import Column, JSON
from enum import Enum
from datetime import datetime, timedelta
from sqlmodel import Session, select, SQLModel, Field
import importlib
import asyncio


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


DEFAULT_EXPIRE = timedelta(days=1)


class TaskItem(SQLModel, table=True):
    id: int = Field(primary_key=True)
    args: List[Any] = Field(sa_column=Column(JSON))
    xargs: Dict[str, Any] = Field(sa_column=Column(JSON))
    func: str

    result: Any = Field(sa_column=Column(JSON))
    status: TaskStatus = Field(default=TaskStatus.PENDING)

    expire_at: datetime = Field(default=datetime.now())
    created_at: datetime = Field(default=datetime.now())
    updated_at: datetime = Field(default=datetime.now())


def enqueue_task(
    session: Session,
    fn: Callable[..., Awaitable[Any]],
    args: List[Any],
    kwargs: Dict[str, Any],
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


def dequeue_task(session: Session):
    task = session.exec(
        select(TaskItem).where(
            TaskItem.status == TaskStatus.PENDING,
            TaskItem.expire_at < datetime.now(),
        )
    ).first()

    if not task:
        return None

    future_time = datetime.now() + DEFAULT_EXPIRE
    task.expire_at = future_time
    task.status = TaskStatus.RUNNING
    session.commit()

    session.refresh(task)
    if task.expire_at == future_time and task.status == TaskStatus.RUNNING:
        return task
    else:
        return dequeue_task(session)


async def worker(session: Session):
    while True:
        task = dequeue_task(session)
        if not task:
            await asyncio.sleep(0.1)
            continue

        try:
            fn = importlib.import_module(task.func)
            result = await task.fn(*task.args, **task.kwargs)
        except Exception as e:
            task.result = str(e)
            task.status = TaskStatus.FAILED
            session.commit()
            continue

        task.result = result
        task.status = TaskStatus.COMPLETED
        session.commit()
