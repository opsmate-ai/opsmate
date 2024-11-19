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
from opsmate.libs.knowledge.schema import Runbook, get_runbooks_table

from opsmate.libs.providers.providers import Client as ProviderClient
import structlog
import subprocess
from tests.base import BaseTestCase
import uuid


class OutputModel(BaseModel):
    name: str
    age: int


logger = structlog.get_logger()


class TestExec(BaseTestCase):

    @pytest.fixture
    def client_bag(self):
        return ProviderClient.clients_from_env()

    def test_exec_react_task_with_non_react_output(self, client_bag):
        task = Task(
            metadata=Metadata(name="test-task"),
            spec=TaskSpec(
                contexts=[react_ctx],
                response_model=OutputModel,
                instruction="test",
            ),
        )

        result = exec_react_task(client_bag, task)
        with pytest.raises(ValueError, match="Task response model must be ReactOutput"):
            next(result)

    def test_exec_react_task_with_no_react_context(self, client_bag):
        task = Task(
            metadata=Metadata(name="test-task"),
            spec=TaskSpec(
                contexts=[os_ctx],
                response_model=ReactOutput,
                instruction="test",
            ),
        )

        result = exec_react_task(client_bag, task)
        with pytest.raises(
            ValueError, match="React context is required for react task"
        ):
            next(result)

    def test_exec_react_task_with_max_depth_0(self, client_bag):
        task = Task(
            metadata=Metadata(name="test-task"),
            spec=TaskSpec(
                contexts=[react_ctx], response_model=ReactOutput, instruction="test"
            ),
        )

        result = exec_react_task(client_bag, task, max_depth=0)
        with pytest.raises(ValueError, match="Max depth must be greater than 0"):
            next(result)

    def test_exec_react_task_with_cli_ctx(self, client_bag):
        task = Task(
            metadata=Metadata(name="test-task"),
            spec=TaskSpec(
                contexts=[cli_ctx, react_ctx],
                response_model=ReactOutput,
                # xxx: not use `lsb_release` command as `No LSB modules are available` is shown on the Github Actions runner
                instruction="what's the name of the operating system distro? do not use `lsb_release` command to find the answer",
            ),
        )

        historic_context = []
        result = exec_react_task(client_bag, task, historic_context=historic_context)
        for output in result:
            logger.info(output)

        assert isinstance(output, ReactAnswer)

        # test there is a ReactProcess in the historic context
        assert any(isinstance(ctx, ReactProcess) for ctx in historic_context)
        assert any(isinstance(ctx, Observation) for ctx in historic_context)
        assert any(isinstance(ctx, ReactAnswer) for ctx in historic_context)

    def test_exec_react_task_with_resolved_answer(self, client_bag):
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
        result = exec_react_task(client_bag, task, historic_context=historic_context)
        for output in result:
            logger.info(output)

        assert isinstance(output, ReactAnswer)

        # assert the pid has been killed

        assert process.poll() is not None

    def test_exec_react_task_make_sure_not_lazy(self, client_bag):
        task = Task(
            metadata=Metadata(name="test-task"),
            spec=TaskSpec(
                contexts=[cli_ctx, react_ctx],
                response_model=ReactOutput,
                instruction="what's the current date?",
            ),
        )

        historic_context = []
        result = exec_react_task(client_bag, task, historic_context=historic_context)
        for output in result:
            logger.info(output)

        assert isinstance(output, ReactAnswer)

        # test there is a ReactProcess in the historic context
        assert any(isinstance(ctx, ReactProcess) for ctx in historic_context)
        assert any(isinstance(ctx, Observation) for ctx in historic_context)
        assert any(isinstance(ctx, ReactAnswer) for ctx in historic_context)

    def test_exec_react_task_with_knowledge_base_query(self, client_bag):
        task = Task(
            metadata=Metadata(name="test-task"),
            spec=TaskSpec(
                contexts=[cli_ctx, react_ctx],
                response_model=ReactOutput,
                instruction="temporarily store the xyz parameter based on the knowledge base?",
            ),
        )

        get_runbooks_table().add(
            [
                {
                    "uuid": str(uuid.uuid4()),
                    "filename": "xyz-manual.txt",
                    "heading": "how to store xyz",
                    "content": """
                    ```bash
                    echo "xyz" > /tmp/xyz
                    ```
                    """,
                }
            ]
        )
        historic_context = []
        result = exec_react_task(client_bag, task, historic_context=historic_context)

        for output in result:
            logger.info(output)

        assert isinstance(output, ReactAnswer)

        # find observation in the historic_context
        found_observation = False
        for ctx in historic_context:
            if isinstance(ctx, Observation):
                if "echo" in ctx.observation and "/tmp/xyz" in ctx.observation:
                    found_observation = True
                    break
        assert found_observation
