import pytest

from opsmate.libs.core.types import (
    Task,
    TaskSpec,
    Metadata,
    ReactOutput,
    ReactAnswer,
    Observation,
    ReactProcess,
)
from opsmate.libs.core.engine.exec import exec_react_task
from opsmate.libs.core.contexts import react_ctx, os_ctx, cli_ctx
from pydantic import BaseModel
from openai import Client
import structlog
import subprocess


class OutputModel(BaseModel):
    name: str
    age: int


logger = structlog.get_logger()


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


def test_exec_react_task_with_cli_ctx(client):
    task = Task(
        metadata=Metadata(name="test-task"),
        spec=TaskSpec(
            contexts=[cli_ctx, react_ctx],
            response_model=ReactOutput,
            instruction="what's the name of the operating system distro?",
        ),
    )

    historic_context = []
    result = exec_react_task(client, task, historic_context=historic_context)
    for output in result:
        logger.info(output)

    assert isinstance(output, ReactAnswer)

    # test there is a ReactProcess in the historic context
    assert any(isinstance(ctx, ReactProcess) for ctx in historic_context)
    assert any(isinstance(ctx, Observation) for ctx in historic_context)
    assert any(isinstance(ctx, ReactAnswer) for ctx in historic_context)


def test_exec_react_task_with_resolved_answer(client):
    # start a "sleep infinity" bash process
    process = subprocess.Popen(
        ["sleep", "infinity"], stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )

    task = Task(
        metadata=Metadata(name="test-task"),
        spec=TaskSpec(
            contexts=[cli_ctx, react_ctx],
            response_model=ReactOutput,
            instruction="can you kill the 'sleep infinity' process?",
        ),
    )

    historic_context = []
    result = exec_react_task(client, task, historic_context=historic_context)
    for output in result:
        logger.info(output)

    assert isinstance(output, ReactAnswer)

    # assert the pid has been killed

    assert process.poll() is not None


def test_exec_react_task_make_sure_not_lazy(client):
    task = Task(
        metadata=Metadata(name="test-task"),
        spec=TaskSpec(
            contexts=[cli_ctx, react_ctx],
            response_model=ReactOutput,
            instruction="what's the current date?",
        ),
    )

    historic_context = []
    result = exec_react_task(client, task, historic_context=historic_context)
    for output in result:
        logger.info(output)

    assert isinstance(output, ReactAnswer)

    # test there is a ReactProcess in the historic context
    assert any(isinstance(ctx, ReactProcess) for ctx in historic_context)
    assert any(isinstance(ctx, Observation) for ctx in historic_context)
    assert any(isinstance(ctx, ReactAnswer) for ctx in historic_context)
