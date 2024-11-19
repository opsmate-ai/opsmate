from opsmate.libs.core.types import (
    ReactOutput,
    Agent,
    ReactAnswer,
    Observation,
)
from opsmate.libs.core.contexts import react_ctx
from opsmate.libs.providers import ClientBag, Client as ProviderClient
from opsmate.libs.core.engine.exec import exec_task, exec_react_task, render_context
from opsmate.libs.agents import AgentCommand
from opsmate.libs.core.trace import traceit
from typing import List, Generator
import yaml
import instructor
import structlog
from queue import Queue

logger = structlog.get_logger()


@traceit(exclude=["client"])
def gen_agent_commands(
    client_bag: ClientBag, supervisor: Agent, action: str
) -> List[AgentCommand]:
    provider_client = ProviderClient(client_bag, supervisor.spec.provider)

    agent_info = []
    for _, agent in supervisor.spec.agents.items():
        agent_info.append(
            f"- name: {agent.metadata.name}\ndescription: {agent.metadata.description}\n"
        )

    # messages = []
    for ctx in supervisor.status.historical_context:
        provider_client.assistant_content(yaml.dump(ctx.model_dump()))
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
{agent_info}
</agents>

<action>
{action}
</action>

Come up with a list of agent commands to execute
"""
    provider_client.system_content(ctx)
    resp = provider_client.chat_completion(
        model=supervisor.spec.model,
        response_model=List[AgentCommand],
    )

    # deduplicate the commands
    agents = {}
    for command in resp:
        if command.agent not in agents:
            agents[command.agent] = command
        else:
            agents[command.agent].instruction += "\n" + command.instruction

    return list(agents.values())


class AgentExecutor:
    def __init__(self, client_bag: ClientBag, ask: bool = False):
        self.client_bag = client_bag
        self.ask = ask

    @traceit(exclude=["stream_output"])
    def supervise(
        self,
        supervisor: Agent,
        instruction: str,
        stream: bool = False,
        stream_output: Queue = None,
    ):
        provider_client = ProviderClient(self.client_bag, supervisor.spec.provider)

        prompt = "\n".join(
            render_context(ctx) for ctx in supervisor.spec.task_template.spec.contexts
        )

        for ctx in supervisor.status.historical_context:
            provider_client.assistant_content(yaml.dump(ctx.model_dump()))

        provider_client.system_content(prompt)
        provider_client.user_content(yaml.dump({"question": instruction}))

        for _ in range(supervisor.spec.max_depth):
            resp = provider_client.chat_completion(
                model=supervisor.spec.model,
                response_model=ReactOutput,
            )

            supervisor.status.historical_context.append(resp.output)

            if isinstance(resp.output, ReactAnswer):
                logger.info(
                    "ReactAnswer",
                    answer=resp.output.answer,
                )
                yield ("@supervisor", resp.output)
                break

            logger.info(
                "ReactOutput",
                thought=resp.output.thought,
                action=resp.output.action,
            )

            provider_client.user_content(yaml.dump(resp.output.model_dump()))
            yield ("@supervisor", resp.output)
            if resp.output.action is not None:
                instruction = yaml.dump(
                    {
                        "thought": resp.output.thought,
                        "action": resp.output.action,
                    }
                )
                commands = gen_agent_commands(self.client_bag, supervisor, instruction)
                for command in commands:
                    agent_name = (
                        f"@{supervisor.spec.agents[command.agent].metadata.name}"
                    )
                    yield (agent_name, command)
                outputs = []
                for command in commands:
                    output = self.execute(
                        supervisor.spec.agents[command.agent],
                        command.instruction,
                        stream=stream,
                        stream_output=stream_output,
                    )

                    agent_name = (
                        f"@{supervisor.spec.agents[command.agent].metadata.name}"
                    )
                    # check if output is a generator
                    if isinstance(output, Generator):
                        for step in output:
                            logger.info("Step", step=step, agent=agent_name)
                            yield (agent_name, step)
                            if isinstance(step, ReactAnswer):
                                outputs.append(step.model_dump())
                                break
                    else:
                        logger.info("Output", output=output, agent=agent_name)
                        yield (agent_name, output)
                        outputs.append(output.model_dump())

                outputs = yaml.dump(outputs)
                observation = Observation(
                    action=resp.output.action,
                    observation=outputs,
                )
                yield ("@supervisor", observation)

                logger.info(
                    "Observation",
                    action=observation.action,
                    observation=observation.observation,
                )
                provider_client.user_content(yaml.dump(observation.model_dump()))

    @traceit(exclude=["stream_output"])
    def execute(
        self,
        agent: Agent,
        instruction: str,
        stream: bool = False,
        stream_output: Queue = None,
    ):
        if agent.spec.react_mode:
            return exec_react_task(
                self.client_bag,
                agent.task(instruction),
                ask=self.ask,
                historic_context=agent.status.historical_context,
                max_depth=agent.spec.max_depth,
                provider=agent.spec.provider,
                model=agent.spec.model,
                stream=stream,
                stream_output=stream_output,
            )
        else:
            return exec_task(
                self.client_bag,
                agent.task(instruction),
                ask=self.ask,
                provider=agent.spec.provider,
                model=agent.spec.model,
                stream=stream,
                stream_output=stream_output,
            )

    def clear_history(self, agent: Agent):
        logger.info("Clearing history for agent", agent=agent.metadata.name)
        agent.status.historical_context = []
        for agent in agent.spec.agents.values():
            self.clear_history(agent)
