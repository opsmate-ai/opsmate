from opsmate.dino.types import ToolCall, PresentationMixin
from pydantic import Field
from typing import Any
from .runtime import MySQLRuntime


class MySQLTool(ToolCall[str], PresentationMixin):
    """MySQL tool"""

    query: str = Field(description="The query to execute")
    timeout: int = Field(
        default=30, ge=1, le=120, description="The timeout for the query in seconds"
    )

    async def __call__(self, context: dict[str, Any] = {}):
        runtime = context.get("runtime")
        if not isinstance(runtime, MySQLRuntime):
            raise RuntimeError("MySQL runtime not found")
        return await runtime.run(self.query, timeout=self.timeout)

    def markdown(self, context: dict[str, Any] = {}):
        return self.output
