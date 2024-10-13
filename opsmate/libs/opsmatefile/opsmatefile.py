from opsmate.libs.core.types import *
from opsmate.libs.contexts import available_contexts as _available_contexts
from opsmate.libs.core.agents import (
    available_agents as _available_agents,
    AgentFactory,
    supervisor_agent,
)
from typing import Optional
import yaml


class World(BaseModel):
    agent_factories: Dict[str, AgentFactory] = Field(
        default_factory=lambda: _available_agents
    )
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

        manifest["spec"]["agents"] = [
            self.agent_factories[agent] for agent in manifest["spec"]["agents"]
        ]

        manifest["spec"]["contexts"] = [
            self.contexts[ctx] for ctx in manifest["spec"]["contexts"]
        ]

        self.supervisor = Supervisor(**manifest)

    def supervisor_agent(
        self,
        model: str = "gpt-4o",
        react_mode: bool = False,
        max_depth: int = 10,
        historical_context: ReactContext = [],
    ):
        agents = [
            agent(model, react_mode, max_depth) for agent in self.supervisor.spec.agents
        ]
        return supervisor_agent(
            model=model,
            agents=agents,
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
