from opsmate.dino.types import (
    ToolCall,
    ToolCallConfig,
    register_tool,
    PresentationMixin,
)
from pydantic import Field
from typing import Any, Tuple, Dict, Union, List
from .runtime import MySQLRuntime, RuntimeError
import pandas as pd

ResultType = Union[
    Tuple[Dict[str, Any], ...],
    List[Dict[str, Any]],
]


class MySQLToolConfig(ToolCallConfig):
    runtime: str = Field(
        alias="MYSQL_TOOL_RUNTIME",
        description="The runtime to use for the tool call",
        default="mysql",
    )


@register_tool(config=MySQLToolConfig)
class MySQLTool(ToolCall[ResultType], PresentationMixin):
    """MySQL tool"""

    class Config:
        arbitrary_types_allowed = True

    query: str = Field(description="The query to execute")
    timeout: int = Field(
        default=30, ge=1, le=120, description="The timeout for the query in seconds"
    )

    async def __call__(self, context: dict[str, Any] = {}):
        runtime = self.maybe_runtime(context)
        if runtime is None:
            raise RuntimeError("MySQL runtime not found")

        if not isinstance(runtime, MySQLRuntime):
            raise RuntimeError(f"Runtime {runtime} is not a MySQLRuntime")

        if not await self.confirmation_prompt(context):
            return (
                {
                    "status": "cancelled",
                    "message": "Query execution cancelled by user, try something else.",
                },
            )

        try:
            return await runtime.run(self.query, timeout=self.timeout)
        except RuntimeError as e:
            return (
                {
                    "status": "error",
                    "message": str(e),
                },
            )
        except Exception:
            raise

    def markdown(self, context: dict[str, Any] = {}):
        result = pd.DataFrame(self.output)
        return f"""
## MySQL Query

```sql
{self.query}
```

## Result

{result.to_markdown()}
"""

    def confirmation_fields(self) -> List[str]:
        return ["query"]

    def maybe_runtime(self, context: dict[str, Any] = {}):
        runtimes = context.get("runtimes", {})
        if len(runtimes) == 0:
            return None

        return runtimes.get("MySQLTool", None)
