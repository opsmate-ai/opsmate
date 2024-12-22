import subprocess
from typing import Optional
from pydantic import Field
from opsmate.dino.types import ToolCall
import structlog

logger = structlog.get_logger(__name__)


class ShellCommand(ToolCall):
    """
    The command to run
    """

    command: str = Field(description="The command to run")
    output: Optional[str] = None

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
{self.command}
```

### Output

```bash
{self.output}
```
"""
