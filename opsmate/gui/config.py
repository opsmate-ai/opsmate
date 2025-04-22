from opsmate.config import Config as OpsmateConfig
from pydantic import Field
from opsmate.plugins import PluginRegistry
from opsmate.dino.context import ContextRegistry


class Config(OpsmateConfig):
    session_name: str = Field(default="session", alias="OPSMATE_SESSION_NAME")
    token: str = Field(default="", alias="OPSMATE_TOKEN")

    system_prompt: str = Field(
        alias="OPSMATE_SYSTEM_PROMPT",
        default="",
    )

    def addon_discovery(self):
        PluginRegistry.discover(self.plugins_dir)
        ContextRegistry.discover(self.contexts_dir)


config = Config()
