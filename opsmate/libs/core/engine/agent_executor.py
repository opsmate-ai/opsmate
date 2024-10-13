from openai import Client
from opsmate.libs.core.types import (
    ReactOutput,
    Agent,
    ReactAnswer,
    Observation,
)
from opsmate.libs.core.contexts import react_ctx
from opsmate.libs.core.engine.exec import exec_task, exec_react_task, render_context
from opsmate.libs.core.agents import AgentCommand
from opsmate.libs.core.trace import traceit
from typing import List, Generator
import yaml
import instructor
import structlog

logger = structlog.get_logger()


@traceit
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

    # deduplicate the commands
    agents = {}
    for command in resp:
        if command.agent not in agents:
            agents[command.agent] = command
        else:
            agents[command.agent].instruction += "\n" + command.instruction

    return agents.values()


class AgentExecutor:
    def __init__(self, client: Client, ask: bool = False):
        self.client = client
        self.ask = ask

    @traceit
    def supervise(self, supervisor: Agent, instruction: str):
        instructor_client = instructor.from_openai(self.client)

        prompt = "\n".join(
            render_context(ctx) for ctx in supervisor.spec.task_template.spec.contexts
        )

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
                question=resp.output.question,
                thought=resp.output.thought,
                action=resp.output.action,
            )

            messages.append(
                {"role": "system", "content": yaml.dump(resp.output.model_dump())}
            )
            yield ("@supervisor", resp.output)
            if resp.output.action is not None:
                instruction = f"""
Here is the question: {resp.output.question}
Here is the thought: {resp.output.thought}
Please execute the action: {resp.output.action}
                        """
                commands = gen_agent_commands(self.client, supervisor, instruction)
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
                yield observation

                logger.info(
                    "Observation",
                    action=observation.action,
                    observation=observation.observation,
                )
                messages.append(
                    {"role": "user", "content": yaml.dump(observation.model_dump())}
                )

    @traceit
    def execute(self, agent: Agent, instruction: str):
        if agent.spec.react_mode:
            return exec_react_task(
                self.client,
                agent.task(instruction),
                ask=self.ask,
                historic_context=agent.status.historical_context,
                max_depth=agent.spec.max_depth,
                model=agent.spec.model,
            )
        else:
            return exec_task(
                self.client,
                agent.task(instruction),
                ask=self.ask,
                model=agent.spec.model,
            )

    def clear_history(self, agent: Agent):
        logger.info("Clearing history for agent", agent=agent.metadata.name)
        agent.status.historical_context = []
        for agent in agent.spec.agents.values():
            self.clear_history(agent)
