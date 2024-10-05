from opsmate.libs.core.types import (
    Metadata,
    ReactOutput,
    Agent,
    AgentSpec,
    TaskTemplate,
    TaskSpecTemplate,
    AgentStatus,
    Context,
    ContextSpec,
    ReactContext,
    BaseTaskOutput,
)
from opsmate.libs.core.contexts import react_ctx, cli_ctx
from pydantic import BaseModel, Field
from typing import List


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


def cli_agent(
    model: str = "gpt-4o",
    react_mode: bool = False,
    max_depth: int = 10,
    historical_context: ReactContext = [],
):
    return Agent(
        metadata=Metadata(
            name="CLI Agent",
            description="Agent to run CLI commands",
            apiVersion="v1",
        ),
        status=AgentStatus(
            historical_context=historical_context,
        ),
        spec=AgentSpec(
            react_mode=react_mode,
            model=model,
            max_depth=max_depth,
            description="Agent to run CLI commands",
            task_template=TaskTemplate(
                metadata=Metadata(
                    name="cli tool",
                    apiVersion="v1",
                    description="Run CLI command",
                ),
                spec=TaskSpecTemplate(
                    contexts=[cli_ctx],
                    response_model=BaseTaskOutput,
                ),
            ),
        ),
    )
