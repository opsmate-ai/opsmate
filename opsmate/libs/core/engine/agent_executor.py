from openai import Client
from opsmate.libs.core.types import (
    ReactContext,
    Task,
    TaskSpec,
    Metadata,
    ReactOutput,
    Agent,
    AgentSpec,
    TaskTemplate,
    TaskSpecTemplate,
    AgentStatus,
    ReactAnswer,
    Observation,
    Context,
    ContextSpec,
)
from opsmate.libs.core.contexts import react_ctx
from opsmate.libs.core.engine.exec import exec_task, exec_react_task, render_context
from pydantic import BaseModel, Field
from typing import List
import yaml
import instructor
import structlog

logger = structlog.get_logger()


class AgentCommand(BaseModel):
    agent: str = Field(..., description="The agent to execute")
    instruction: str = Field(..., description="The instruction to execute")
    ask: bool = Field(False, description="Whether to ask for confirmation")


def supervisor_agent(
    model: str = "gpt-4o", agents: List[Agent] = [], extra_context: str = ""
):
    agent_map = {agent.metadata.name: agent for agent in agents}

    contexts = [react_ctx]
    if extra_context != "":
        ctx = Context(
            metadata=Metadata(
                name="Agent Supervisor",
                apiVersion="v1",
                description="Supervisor to execute agent commands",
            ),
            spec=ContextSpec(
                data=extra_context,
            ),
        )
    return Agent(
        metadata=Metadata(
            name="Agent Supervisor",
            apiVersion="v1",
            description="Supervisor to execute agent commands",
        ),
        status=AgentStatus(),
        spec=AgentSpec(
            react_mode=True,
            model=model,
            max_depth=10,
            agents=agent_map,
            description="Supervisor to execute agent commands",
            task_template=TaskTemplate(
                metadata=Metadata(
                    name="Agent Supervisor",
                    apiVersion="v1",
                    description="Supervisor to execute agent commands",
                ),
                spec=TaskSpecTemplate(
                    contexts=contexts,
                    response_model=ReactOutput,
                ),
            ),
        ),
    )


def gen_agent_commands(client: Client, supervisor: Agent, action: str):
    agents_context = []
    for _, agent in supervisor.spec.agents.items():
        agents_context.append(
            f"- name: {agent.metadata.name}\ndescription: {agent.metadata.description}\n"
        )

    ctx = f"""
based on the action, and available agents, comes up with a list of instructions for the agents to execute

Example 1:

Available Agents:

- name: k8s_agent
  description: Agent to manage the k8s clusters
- name: slack_agent
  description: Agent to send messages to slack

Action: "Investigate the OOMKilled error in the k8s cluster"

Agent Commands:

- k8s_agent: "Check the pod events for the OOMKilled error"
- slack_agent: "Send a message to the slack channel about the OOMKilled error"

Now here are the available agents and action:

<agents>
{agents_context}
</agents>

<action>
{action}
</action>

Come up with a list of agent commands to execute
"""
    instructor_client = instructor.from_openai(client)
    resp = instructor_client.chat.completions.create(
        model=supervisor.spec.model,
        messages=[{"role": "user", "content": ctx}],
        response_model=List[AgentCommand],
    )
    return resp


class AgentExecutor:
    def __init__(self, client: Client):
        self.client = client

    def supervise(self, supervisor: Agent, instruction: str, ask: bool = False):
        instructor_client = instructor.from_openai(self.client)

        # prompt = render_context(react_ctx)
        for ctx in supervisor.spec.task_template.spec.contexts:
            prompt = render_context(ctx) + "\n"

        messages = []
        messages.extend(
            {"role": "system", "content": yaml.dump(ctx.model_dump())}
            for ctx in supervisor.status.historical_context
        )

        messages.append({"role": "user", "content": prompt})
        messages.append({"role": "user", "content": "question: " + instruction})

        for _ in range(supervisor.spec.max_depth):
            resp = instructor_client.chat.completions.create(
                model=supervisor.spec.model,
                messages=messages,
                response_model=ReactOutput,
            )

            if isinstance(resp.output, ReactAnswer):
                logger.info(
                    "ReactAnswer",
                    answer=resp.output.answer,
                )
                yield resp
                break

            logger.info(
                "ReactOutput",
                question=resp.output.question,
                thought=resp.output.thought,
                action=resp.output.action,
            )
            yield resp
            if resp.output.action is not None:
                commands = gen_agent_commands(
                    self.client, supervisor, resp.output.action
                )
                outputs = []
                for command in commands:
                    output = self.execute(
                        supervisor.spec.agents[command.agent],
                        command.instruction,
                        command.ask,
                    )
                    yield output
                    outputs.append(output.model_dump())

                outputs = yaml.dump(outputs)
                observation = Observation(
                    action=resp.output.action,
                    observation=outputs,
                )
                yield observation

                logger.info(
                    "Observation",
                    action=observation.action,
                    observation=observation.observation,
                )
                messages.append(
                    {"role": "user", "content": yaml.dump(observation.model_dump())}
                )

    def execute(self, agent: Agent, instruction: str, ask: bool = False):
        if agent.spec.react_mode:
            return exec_react_task(
                self.client,
                agent.task(instruction),
                ask=ask,
                historic_context=agent.status.historical_context,
                max_depth=agent.spec.max_depth,
                model=agent.spec.model,
            )
        else:
            return exec_task(
                self.client,
                agent.task(instruction),
                ask=ask,
                model=agent.spec.model,
            )
