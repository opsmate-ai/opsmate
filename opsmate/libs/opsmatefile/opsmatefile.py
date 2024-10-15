from opsmate.libs.core.types import *
from opsmate.libs.contexts import available_contexts as _available_contexts
from opsmate.libs.agents import (
    available_agents as _available_agents,
    AgentFactory,
    supervisor_agent as _supervisor_agent,
)
from typing import Optional
import yaml


class AgentConfig(BaseModel):
    model: str = "gpt-4o"
    react_mode: bool = True
    max_depth: int = 10
    extra_contexts: List[Context] = []


class World(BaseModel):
    agent_factories: Dict[str, AgentFactory] = Field(
        default_factory=lambda: _available_agents
    )
    agent_configs: Dict[str, AgentConfig] = Field(default={})
    contexts: Dict[str, Context] = Field(
        default_factory=lambda: {ctx.metadata.name: ctx for ctx in _available_contexts}
    )
    supervisor: Optional[Supervisor] = None

    def add_context(self, manifest: Dict):
        if "spec" not in manifest:
            raise ValueError("Context is invalid, missing 'spec' field")
        if "contexts" not in manifest["spec"]:
            manifest["spec"]["contexts"] = []

        manifest["spec"]["contexts"] = [
            self.contexts[ctx] for ctx in manifest["spec"]["contexts"]
        ]

        ctx = Context(**manifest)
        self.contexts[ctx.metadata.name] = ctx

    def add_supervisor(self, manifest: Dict):
        if self.supervisor is not None:
            raise ValueError("Supervisor already exists")

        if "spec" not in manifest:
            raise ValueError("Supervisor is invalid, missing 'spec' field")

        for agent_config in manifest["spec"]["agents"]:
            agent_config["extra_contexts"] = [
                self.contexts[ctx] for ctx in agent_config.get("extra_contexts", [])
            ]
            self.agent_configs[agent_config["name"]] = AgentConfig(**agent_config)

        manifest["spec"]["agents"] = []

        for agent_name in self.agent_configs.keys():
            if agent_name not in self.agent_factories:
                raise ValueError(f"Agent factory for {agent_name} not found")

            manifest["spec"]["agents"].append(
                self.agent_factories[agent_name](
                    **self.agent_configs[agent_name].model_dump()
                )
            )

        manifest["spec"]["contexts"] = [
            self.contexts[ctx] for ctx in manifest["spec"]["contexts"]
        ]

        self.supervisor = Supervisor(**manifest)

    def supervisor_agent(
        self,
    ):
        return _supervisor_agent(
            model=self.supervisor.spec.model,
            max_depth=self.supervisor.spec.max_depth,
            agents=self.supervisor.spec.agents,
            extra_contexts=self.supervisor.spec.contexts,
        )


def load_opsmatefile(path: str = "Opsmatefile"):
    with open(path, "r") as f:
        data = yaml.safe_load_all(f)

        world = World()
        for manifest in data:
            if "kind" not in manifest:
                raise ValueError("Manifest is invalid, missing 'kind' field")

            if manifest["kind"] == "Context":
                world.add_context(manifest)
            elif manifest["kind"] == "Supervisor":
                world.add_supervisor(manifest)

    return world
