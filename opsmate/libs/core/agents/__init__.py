from .agents import *
from typing import Dict
from opsmate.libs.core.types import AgentFactory

available_agents: Dict[str, AgentFactory] = {
    "cli-agent": cli_agent,
    "k8s-agent": k8s_agent,
    "git-agent": git_agent,
}
