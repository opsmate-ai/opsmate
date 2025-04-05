from opsmate.dino.types import ToolCall, PresentationMixin
from pydantic import Field
from typing import Any, Tuple, Dict, Union, List
from .runtime import MySQLRuntime, RuntimeError
import pandas as pd

ResultType = Union[
    Tuple[Dict[str, Any], ...],
    List[Dict[str, Any]],
]


class MySQLTool(ToolCall[ResultType], PresentationMixin):
    """MySQL tool"""

    class Config:
        arbitrary_types_allowed = True

    query: str = Field(description="The query to execute")
    timeout: int = Field(
        default=30, ge=1, le=120, description="The timeout for the query in seconds"
    )

    async def __call__(self, context: dict[str, Any] = {}):
        runtime = context.get("runtime")
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
