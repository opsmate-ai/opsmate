import pytest
from opsmate.libs.agents import (
    get_supervisor_agent_list_context,
    k8s_agent,
    cli_agent,
    supervisor_agent,
)
from opsmate.libs.core.types import Context, ContextSpec, Metadata, ReactOutput
from opsmate.tests.base import BaseTestCase


class TestAgents(BaseTestCase):
    def test_get_supervisor_agent_list_context(self):
        agents = [k8s_agent, cli_agent]
        agents = [agent() for agent in agents]
        context = get_supervisor_agent_list_context(agents)
        assert (
            context.spec.data
            == f"""
Here is the list of agents you are supervising and delegate tasks to:

<agents>
- name: k8s-agent
  description: k8s-agent is specialised in managing and operating kubernetes clusters
- name: cli-agent
  description: cli-agent is specialised in doing system administration tasks on the machine it is running on
</agents>
"""
        )

    def test_supervisor_agent_with_extra_context_as_string(self):
        agents = [k8s_agent, cli_agent]
        agents = [agent() for agent in agents]

        supervisor = supervisor_agent(agents=agents, extra_contexts="extra-context")
        supervisor_contexts = supervisor.spec.task_template.spec.contexts

        extra_context = [
            ctx for ctx in supervisor_contexts if ctx.metadata.name == "extra-context"
        ]
        assert len(extra_context) == 1
        assert extra_context[0].spec.data == "extra-context"

    def test_supervisor_agent_with_extra_context_as_list(self):
        agents = [k8s_agent, cli_agent]
        agents = [agent() for agent in agents]

        extra_contexts = [
            Context(
                metadata=Metadata(
                    name="extra-context",
                    description="Extra context to use",
                ),
                spec=ContextSpec(data="extra-context"),
            ),
            Context(
                metadata=Metadata(
                    name="extra-context-2",
                    description="Extra context to use",
                ),
                spec=ContextSpec(data="extra-context-2"),
            ),
        ]

        supervisor = supervisor_agent(agents=agents, extra_contexts=extra_contexts)
        supervisor_contexts = supervisor.spec.task_template.spec.contexts

        contexts_names = [ctx.metadata.name for ctx in supervisor_contexts]
        assert "extra-context" in contexts_names
        assert "extra-context-2" in contexts_names

    def test_supervisor_agent_with_extra_context_has_react_configures(self):
        agents = [k8s_agent, cli_agent]
        agents = [agent() for agent in agents]

        supervisor = supervisor_agent(agents=agents, extra_contexts="extra-context")
        supervisor_contexts = supervisor.spec.task_template.spec.contexts

        react_context = [
            ctx for ctx in supervisor_contexts if ctx.metadata.name == "react"
        ]
        assert len(react_context) == 1

        assert supervisor.spec.react_mode == True
        assert supervisor.spec.task_template.spec.response_model == ReactOutput

    def test_supervisor_agent_with_extra_context_has_the_correct_subagents(self):
        agents = [k8s_agent, cli_agent]
        agents = [agent() for agent in agents]

        supervisor = supervisor_agent(agents=agents, extra_contexts="extra-context")

        agent_map = supervisor.spec.agents
        assert len(agent_map) == 2
        assert "k8s-agent" in agent_map
        assert "cli-agent" in agent_map
