from typing import Any, List
from pydantic import Field
from opsmate.dino.types import (
    ToolCall,
    ToolCallConfig,
    PresentationMixin,
    register_tool,
)
import structlog
from opsmate.tools.utils import maybe_truncate_text
from opsmate.runtime.local import LocalRuntime, LocalRuntimeConfig
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

tracer = trace.get_tracer(__name__)
logger = structlog.get_logger(__name__)


class ShellCommandConfig(ToolCallConfig):
    runtime: str = Field(
        alias="SHELL_COMMAND_RUNTIME",
        description="The runtime to use for the tool call",
        default="local",
    )


@register_tool(config=ShellCommandConfig)
class ShellCommand(ToolCall[str], PresentationMixin):
    """
    ShellCommand tool allows you to run shell commands and get the output.
    """

    description: str = Field(description="Explain what the command is doing")
    command: str = Field(description="The command to run")
    timeout: float = Field(
        description="The estimated time for the command to execute in seconds",
        default=120.0,
    )

    async def __call__(self, context: dict[str, Any] = {}):
        with tracer.start_as_current_span("shell_command") as span:
            envvars = context.get("envvars", {})
            max_output_length = context.get("max_output_length", 10000)
            logger.info("running shell command", command=self.command)

            runtime = self.maybe_runtime(context)
            transit_runtime = True if runtime is None else False

            span.set_attributes(
                {
                    "runtime": runtime.__class__.__name__,
                    "transit_runtime": transit_runtime,
                    "command": self.command,
                    "description": self.description,
                }
            )

            if not await self.confirmation_prompt(context):
                return "Command execution cancelled by user, try something else."

            if runtime is None:
                runtime = LocalRuntime(LocalRuntimeConfig(envvars=envvars))
                await runtime.connect()

            try:
                out = await runtime.run(self.command, timeout=self.timeout)

                span.set_attributes({"output": out})
                return maybe_truncate_text(out, max_output_length)
            except Exception as e:
                err_msg = str(e)
                span.set_attributes({"error": err_msg})
                span.set_status(Status(StatusCode.ERROR))
                return err_msg
            finally:
                if transit_runtime:
                    await runtime.disconnect()

    def maybe_runtime(self, context: dict[str, Any] = {}):
        runtimes = context.get("runtimes", {})
        if len(runtimes) == 0:
            return None

        return runtimes.get("ShellCommand", None)

    def confirmation_fields(self) -> List[str]:
        return ["command"]

    def markdown(self, context: dict[str, Any] = {}):
        return f"""
### Command

```bash
# {self.description}
{self.command}
```

### Output

```bash
{self.output}
```
"""
