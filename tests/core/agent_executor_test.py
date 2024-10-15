import pytest

from opsmate.libs.core.engine.agent_executor import gen_agent_commands, AgentExecutor
from opsmate.libs.agents import (
    supervisor_agent,
    k8s_agent,
    git_agent,
    cli_agent,
    AgentCommand,
)
from opsmate.libs.core.types import ExecResult, ReactAnswer, ReactProcess, ExecOutput
from opsmate.libs.core.contexts import ExecShell
from openai import Client
from typing import Generator
from queue import Queue


@pytest.fixture
def openai_client():
    return Client()


@pytest.fixture
def model():
    return "gpt-4o-mini"


def test_gen_agent_command_single_agent(openai_client, model):
    supervisor = supervisor_agent(agents=[k8s_agent(), git_agent()], model=model)
    agent_commands = gen_agent_commands(
        openai_client, supervisor, "Investigate the OOMKilled error in the k8s cluster"
    )
    assert len(agent_commands) >= 1

    assert any(agent_cmd.agent == "k8s-agent" for agent_cmd in agent_commands)


def test_gen_agent_command_multiple_agents(openai_client, model):
    supervisor = supervisor_agent(agents=[k8s_agent(), git_agent()], model=model)
    agent_commands = gen_agent_commands(
        openai_client,
        supervisor,
        "find all the namespaces and use them as the commit message",
    )
    assert len(agent_commands) == 2

    assert any(agent_cmd.agent == "k8s-agent" for agent_cmd in agent_commands)
    assert any(agent_cmd.agent == "git-agent" for agent_cmd in agent_commands)


def test_executor_execute(openai_client, model):
    executor = AgentExecutor(client=openai_client)
    agent = cli_agent(model=model)
    result = executor.execute(
        agent=agent, instruction="what's the name of the OS distro"
    )
    assert len(result.calls) == 1
    exec_call = result.calls[0]
    assert exec_call.command != ""

    output = exec_call.output
    assert output.exit_code == 0
    assert output.stdout != ""
    assert output.stderr == ""


def test_executor_execute_stream(openai_client, model):
    executor = AgentExecutor(client=openai_client)
    agent = cli_agent(model=model)
    queue = Queue()
    output = executor.execute(
        agent=agent,
        instruction="what's the name of the OS distro",
        stream=True,
        stream_output=queue,
    )

    assert queue.qsize() > 0
    while not queue.empty():
        chunk = queue.get()
        assert isinstance(chunk, (ExecOutput, ExecShell))


def test_executor_execute_react(openai_client, model):
    executor = AgentExecutor(client=openai_client)
    agent = cli_agent(react_mode=True, model=model)
    output = executor.execute(
        agent=agent, instruction="what's the name of the OS distro"
    )

    assert isinstance(output, Generator)

    last = None
    for chunk in output:
        assert isinstance(chunk, (ReactAnswer, ReactProcess, ExecResult))
        last = chunk

    assert isinstance(last, ReactAnswer)
    assert last.answer != ""


def test_executor_execute_react_stream(openai_client, model):
    executor = AgentExecutor(client=openai_client)
    agent = cli_agent(react_mode=True, model=model)
    queue = Queue()
    output = executor.execute(
        agent=agent,
        instruction="what's the name of the OS distro",
        stream=True,
        stream_output=queue,
    )

    for chunk in output:
        assert isinstance(chunk, (ReactAnswer, ReactProcess, ExecResult))

    assert queue.qsize() > 0
    while not queue.empty():
        chunk = queue.get()
        assert isinstance(chunk, (ExecOutput, ExecShell))


def test_executor_clear_history(openai_client, model):
    executor = AgentExecutor(client=openai_client)
    agent = cli_agent(model=model, react_mode=True)
    output = executor.execute(
        agent=agent, instruction="what's the name of the OS distro"
    )

    # to run through the generator
    assert len(list(output)) > 0

    assert len(agent.status.historical_context) > 0
    executor.clear_history(agent)
    assert len(agent.status.historical_context) == 0
