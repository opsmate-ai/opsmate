from opsmate.config import Config as OpsmateConfig
from pydantic import Field
from opsmate.plugins import PluginRegistry
from opsmate.dino.context import ContextRegistry
from typing import List


class Config(OpsmateConfig):
    session_name: str = Field(default="session", alias="OPSMATE_SESSION_NAME")
    token: str = Field(default="", alias="OPSMATE_TOKEN")

    tools: List[str] = Field(
        default=[
            "ShellCommand",
            "KnowledgeRetrieval",
            "ACITool",
            "HtmlToText",
            "PrometheusTool",
        ],
        alias="OPSMATE_TOOLS",
    )
    system_prompt: str = Field(
        alias="OPSMATE_SYSTEM_PROMPT",
        default="",
    )
    context: str = Field(
        default="k8s",
        alias="OPSMATE_CONTEXT",
        description="The context to use for the session. Run `opsmate list-contexts` to see the available contexts.",
    )

    model: str = Field(
        default="gpt-4o",
        alias="OPSMATE_MODEL",
        choices=["gpt-4o", "claude-3-5-sonnet-20241022", "grok-2-1212"],
    )

    def addon_discovery(self):
        PluginRegistry.discover(self.plugins_dir)
        ContextRegistry.discover(self.contexts_dir)

    def opsmate_tools(self):
        return PluginRegistry.get_tools_from_list(self.tools)


config = Config()
