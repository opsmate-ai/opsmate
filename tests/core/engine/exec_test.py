import pytest

from opsmate.libs.core.types import Task, TaskSpec, Metadata, ReactOutput
from opsmate.libs.core.engine.exec import exec_react_task
from opsmate.libs.core.contexts import react_ctx, os_ctx
from pydantic import BaseModel
from openai import Client


class OutputModel(BaseModel):
    name: str
    age: int


@pytest.fixture
def client():
    return Client()


def test_exec_react_task_with_non_react_output(client):
    task = Task(
        metadata=Metadata(name="test-task"),
        spec=TaskSpec(
            contexts=[react_ctx],
            response_model=OutputModel,
            instruction="test",
        ),
    )

    result = exec_react_task(client, task)
    with pytest.raises(ValueError, match="Task response model must be ReactOutput"):
        next(result)


def test_exec_react_task_with_no_react_context(client):
    task = Task(
        metadata=Metadata(name="test-task"),
        spec=TaskSpec(
            contexts=[os_ctx],
            response_model=ReactOutput,
            instruction="test",
        ),
    )

    result = exec_react_task(client, task)
    with pytest.raises(ValueError, match="React context is required for react task"):
        next(result)


def test_exec_react_task_with_max_depth_0(client):
    task = Task(
        metadata=Metadata(name="test-task"),
        spec=TaskSpec(
            contexts=[react_ctx], response_model=ReactOutput, instruction="test"
        ),
    )

    result = exec_react_task(client, task, max_depth=0)
    with pytest.raises(ValueError, match="Max depth must be greater than 0"):
        next(result)
