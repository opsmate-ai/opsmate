import subprocess
from typing import Optional, ClassVar
from pydantic import Field, PrivateAttr
from opsmate.dino.types import ToolCall, PresentationMixin
import structlog
import asyncio
from opsmate.tools.utils import maybe_truncate_text

logger = structlog.get_logger(__name__)


class ShellCommand(ToolCall[str], PresentationMixin):
    """
    ShellCommand tool allows you to run shell commands and get the output.
    """

    max_text_length: ClassVar[int] = 10000

    description: str = Field(description="Explain what the command is doing")
    command: str = Field(description="The command to run")
    timeout: float = Field(
        description="The estimated time for the command to execute in seconds",
        default=120.0,
    )

    async def __call__(self):
        logger.info("running shell command", command=self.command)
        try:
            process = await asyncio.create_subprocess_shell(
                self.command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            stdout, _ = await asyncio.wait_for(
                process.communicate(), timeout=self.timeout
            )
            return maybe_truncate_text(stdout.decode(), self.max_text_length)
        except Exception as e:
            return str(e)

    def markdown(self):
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
