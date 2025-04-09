from opsmate.dino.types import ToolCall, PresentationMixin, register_tool
from typing import Any
from pydantic import Field
import structlog

logger = structlog.get_logger(__name__)


@register_tool()
class Thinking(ToolCall[str], PresentationMixin):
    """
    Use the tool to think about something.
    It will not obtain new information or change the system state,
    but just append the thought to the log.

    Use this tool when there is no obvious action to take.
    """

    thought: str = Field(description="The thought to think about")

    async def __call__(self, context: dict[str, Any] = {}):
        logger.info("thinking", thought=self.thought)
        return self.thought

    def markdown(self, context: dict[str, Any] = {}):
        return f"""
### Thought

{self.thought}
"""
