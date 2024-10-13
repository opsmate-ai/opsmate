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
    # BaseTaskOutput,
    ExecResult,
)
from opsmate.libs.core.contexts import react_ctx, cli_ctx
from opsmate.libs.contexts import k8s_ctx, git_ctx
from pydantic import BaseModel, Field
from typing import List, Callable


class AgentCommand(BaseModel):
    agent: str = Field(..., description="The agent to execute")
    instruction: str = Field(..., description="The instruction to execute")
    # ask: bool = Field(False, description="Whether to ask for confirmation")


def supervisor_agent(
    model: str = "gpt-4o",
    max_depth: int = 10,
    agents: List[Agent] = [],
    extra_contexts: str | List[Context] = "",
):
    agent_map = {agent.metadata.name: agent for agent in agents}

    agent_context = Context(
        metadata=Metadata(
            name="agent-supervisor",
            description="Supervisor to execute agent commands",
        ),
        spec=ContextSpec(
            data="""
Here is the list of agents you are supervising:

<agents>
{agents}
</agents>

""".format(
                agents="\n".join(
                    [
                        f"- {agent.metadata.name}: {agent.metadata.description}"
                        for agent in agents
                    ]
                )
            ),
        ),
    )
    contexts = [agent_context]
    if isinstance(extra_contexts, str):
        if extra_contexts != "":
            ctx = Context(
                metadata=Metadata(
                    name="agent-supervisor",
                    description="Supervisor to execute agent commands",
                ),
                spec=ContextSpec(
                    data=extra_contexts,
                ),
            )
            contexts.append(ctx)
    elif isinstance(extra_contexts, list):
        contexts.extend(extra_contexts)

    contexts.append(react_ctx)
    return Agent(
        metadata=Metadata(
            name="agent-supervisor",
            description="Supervisor to execute agent commands",
        ),
        status=AgentStatus(),
        spec=AgentSpec(
            react_mode=True,
            model=model,
            max_depth=max_depth,
            agents=agent_map,
            description="Supervisor to execute agent commands",
            task_template=TaskTemplate(
                metadata=Metadata(
                    name="agent-supervisor",
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
    extra_contexts: List[Context] = [],
):
    contexts = []
    contexts.extend(extra_contexts)
    contexts.append(cli_ctx)
    response_model = ExecResult

    if react_mode:
        contexts.append(react_ctx)
        response_model = ReactOutput

    return Agent(
        metadata=Metadata(
            name="cli-agent",
            description="Agent to run CLI commands",
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
                    description="Run CLI command",
                ),
                spec=TaskSpecTemplate(
                    contexts=contexts,
                    response_model=response_model,
                ),
            ),
        ),
    )


def k8s_agent(
    model: str = "gpt-4o",
    react_mode: bool = False,
    max_depth: int = 10,
    historical_context: ReactContext = [],
    extra_contexts: List[Context] = [],
):
    contexts = []
    contexts.extend(extra_contexts)
    contexts.append(k8s_ctx)
    response_model = ExecResult

    if react_mode:
        contexts.append(react_ctx)
        response_model = ReactOutput

    return Agent(
        metadata=Metadata(
            name="k8s-agent",
            description="Agent to run K8S commands",
        ),
        status=AgentStatus(
            historical_context=historical_context,
        ),
        spec=AgentSpec(
            react_mode=react_mode,
            model=model,
            max_depth=max_depth,
            description="Agent to run K8S commands",
            task_template=TaskTemplate(
                metadata=Metadata(
                    name="k8s tool",
                    description="Run K8S command",
                ),
                spec=TaskSpecTemplate(
                    contexts=contexts,
                    response_model=response_model,
                ),
            ),
        ),
    )


def git_agent(
    model: str = "gpt-4o",
    react_mode: bool = False,
    max_depth: int = 10,
    historical_context: ReactContext = [],
    extra_contexts: List[Context] = [],
):
    contexts = []
    contexts.extend(extra_contexts)
    contexts.append(git_ctx)
    response_model = ExecResult

    if react_mode:
        contexts.append(react_ctx)
        response_model = ReactOutput

    return Agent(
        metadata=Metadata(
            name="git-agent",
            description="Agent to run git commands",
        ),
        status=AgentStatus(
            historical_context=historical_context,
        ),
        spec=AgentSpec(
            react_mode=react_mode,
            model=model,
            max_depth=max_depth,
            description="Agent to run git commands",
            task_template=TaskTemplate(
                metadata=Metadata(
                    name="git tool",
                    description="Run git command",
                ),
                spec=TaskSpecTemplate(
                    contexts=contexts,
                    response_model=response_model,
                ),
            ),
        ),
    )
