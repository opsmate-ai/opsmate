import subprocess
from typing import Optional
from pydantic import Field
from opsmate.dino.types import ToolCall
import structlog

logger = structlog.get_logger(__name__)


class ShellCommand(ToolCall):
    """
    ShellCommand tool allows you to run shell commands and get the output.
    """

    description: str = Field(description="Explain what the command is doing")
    command: str = Field(description="The command to run")
    output: Optional[str] = Field(
        description="The output of the command - DO NOT POPULATE"
    )

    def __call__(self):
        logger.info("running shell command", command=self.command)
        try:
            result = subprocess.run(
                self.command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            self.output = result.stdout
        except subprocess.SubprocessError as e:
            self.output = str(e)
        return self.output

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
