import pytest

from opsmate.libs.core.engine.agent_executor import gen_agent_commands, AgentExecutor
from opsmate.libs.agents import (
    supervisor_agent,
    k8s_agent,
    git_agent,
    cli_agent,
    AgentCommand,
)
from opsmate.libs.core.types import (
    ExecResults,
    ReactAnswer,
    ReactProcess,
    ExecOutput,
    ReactOutput,
    Agent,
    AgentSpec,
    TaskSpec,
    TaskTemplate,
    TaskSpecTemplate,
    Context,
    ContextSpec,
    Metadata,
    AgentStatus,
    Observation,
)
from opsmate.libs.core.contexts import ExecShell, react_ctx

from opsmate.libs.providers.providers import Client as ProviderClient
from typing import Generator
from queue import Queue
from tests.base import BaseTestCase


class TestAgentExecutor(BaseTestCase):

    @pytest.fixture
    def client_bag(self):
        return ProviderClient.clients_from_env()

    @pytest.fixture
    def model(self):
        return "gpt-4o"

    def test_gen_agent_command_single_agent(self, client_bag, model):
        supervisor = supervisor_agent(agents=[k8s_agent(), git_agent()], model=model)
        agent_commands = gen_agent_commands(
            client_bag,
            supervisor,
            "Investigate the OOMKilled error in the k8s cluster",
        )
        assert len(agent_commands) >= 1

        assert any(agent_cmd.agent == "k8s-agent" for agent_cmd in agent_commands)

    def test_gen_agent_command_multiple_agents(self, client_bag, model):
        supervisor = supervisor_agent(agents=[k8s_agent(), git_agent()], model=model)
        agent_commands = gen_agent_commands(
            client_bag,
            supervisor,
            "find all the namespaces and use them as the commit message",
        )
        assert len(agent_commands) == 2

        assert any(agent_cmd.agent == "k8s-agent" for agent_cmd in agent_commands)
        assert any(agent_cmd.agent == "git-agent" for agent_cmd in agent_commands)

    def distro_question(self):
        return "what's the name of the OS distro? do not use `lsb_release` command to find the answer"

    def test_executor_execute(self, client_bag, model):
        executor = AgentExecutor(client_bag=client_bag)
        agent = cli_agent(model=model)
        output = executor.execute(
            agent=agent,
            instruction=self.distro_question(),
        )

        for result in output.results:
            assert result.exit_code == 0
            assert result.stdout != ""
            assert result.stderr == ""

    def test_executor_execute_stream(self, client_bag, model):
        executor = AgentExecutor(client_bag=client_bag)
        agent = cli_agent(model=model)
        queue = Queue()
        output = executor.execute(
            agent=agent,
            instruction=self.distro_question(),
            stream=True,
            stream_output=queue,
        )

        assert queue.qsize() > 0
        while not queue.empty():
            chunk = queue.get()
            assert isinstance(chunk, (ExecOutput, ExecShell))

    def test_executor_execute_react(self, client_bag, model):
        executor = AgentExecutor(client_bag=client_bag)
        agent = cli_agent(react_mode=True, model=model)
        output = executor.execute(
            agent=agent,
            instruction=self.distro_question(),
        )

        assert isinstance(output, Generator)

        last = None
        for chunk in output:
            assert isinstance(chunk, (ReactAnswer, ReactProcess, ExecResults))
            last = chunk

        assert isinstance(last, ReactAnswer)
        assert last.answer != ""

    def test_executor_execute_react_stream(self, client_bag, model):
        executor = AgentExecutor(client_bag=client_bag)
        agent = cli_agent(react_mode=True, model=model)
        queue = Queue()
        output = executor.execute(
            agent=agent,
            instruction="what's the name of the OS distro",
            stream=True,
            stream_output=queue,
        )

        for chunk in output:
            assert isinstance(chunk, (ReactAnswer, ReactProcess, ExecResults))

        assert queue.qsize() > 0
        while not queue.empty():
            chunk = queue.get()
            assert isinstance(chunk, (ExecOutput, ExecShell))

    def test_executor_clear_history(self, client_bag, model):
        executor = AgentExecutor(client_bag=client_bag)
        agent = cli_agent(model=model, react_mode=True)
        output = executor.execute(
            agent=agent, instruction="what's the name of the OS distro"
        )

        # to run through the generator
        assert len(list(output)) > 0

        assert len(agent.status.historical_context) > 0
        executor.clear_history(agent)
        assert len(agent.status.historical_context) == 0

    @pytest.fixture
    def math_agent(self):
        return Agent(
            metadata=Metadata(name="math-agent", description="agent does math"),
            spec=AgentSpec(
                model="gpt-4o",
                react_mode=True,
                max_depth=10,
                task_template=TaskTemplate(
                    metadata=Metadata(name="math-task", description="task for math"),
                    spec=TaskSpecTemplate(
                        contexts=[
                            Context(
                                metadata=Metadata(
                                    name="math-context", description="context for math"
                                ),
                                spec=ContextSpec(
                                    data="You are a helpful assistant that does math, you can use shell commands for calculations",
                                    executables=[ExecShell],
                                ),
                            ),
                            react_ctx,
                        ],
                        response_model=ReactOutput,
                    ),
                ),
            ),
            status=AgentStatus(historical_context=[]),
        )

    def test_supervisor_agent_reasoning(self, client_bag, math_agent, model):
        supervisor = supervisor_agent(
            agents=[math_agent],
            model=model,
        )

        executor = AgentExecutor(client_bag=client_bag)
        result = executor.supervise(
            supervisor, "a = 1, b = 2, a + b = ?, delegate the task to the agent"
        )
        assert isinstance(result, Generator)

        for output in result:
            assert isinstance(output, tuple)
            assert len(output) == 2

            agent_name, output = output

            assert agent_name in ["@math-agent", "@supervisor"]

            if agent_name == "@supervisor":
                assert isinstance(output, (ReactAnswer, ReactProcess, Observation))
            elif agent_name == "@math-agent":
                assert isinstance(
                    output,
                    (AgentCommand, ReactAnswer, ReactProcess, ExecResults, Observation),
                )
