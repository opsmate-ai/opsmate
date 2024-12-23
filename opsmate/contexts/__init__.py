from .k8s import k8s_ctx, k8s_tools
from .terraform import terraform_ctx, terraform_tools
from .cli import cli_ctx, cli_tools
from pydantic import BaseModel
from typing import Callable, List, Type
from opsmate.dino.types import ToolCall

__all__ = ["k8s_ctx", "k8s_tools", "terraform_ctx", "terraform_tools"]


class Context(BaseModel):
    description: str
    ctx: Callable[[], str]
    tools: List[Type[ToolCall]]


contexts = {
    "cli": Context(
        description="General purpose context for solving problems on the command line.",
        ctx=cli_ctx,
        tools=cli_tools(),
    ),
    "k8s": Context(
        description="Kubernetes context for solving problems on Kubernetes.",
        ctx=k8s_ctx,
        tools=k8s_tools(),
    ),
    "terraform": Context(
        description="Terraform context for running Terraform based IaC commands.",
        ctx=terraform_ctx,
        tools=terraform_tools(),
    ),
}
