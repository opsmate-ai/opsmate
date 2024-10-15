from opsmate.libs.core.contexts import (
    Context,
    ContextSpec,
    Metadata,
    Executable,
    ExecShell,
)
from opsmate.libs.core.contexts import os_ctx
import shutil
import subprocess
from opsmate.libs.core.trace import traceit
from pydantic import Field

tools = ["terraform"]


class Terraform(Executable):
    def __call__(self, *args, **kwargs):
        return [tool for tool in tools if shutil.which(tool)]


class TerraformHelp(Executable):
    def __call__(self, *args, **kwargs):
        return subprocess.run(["terraform", "help"], capture_output=True)


class ExecTerraform(ExecShell):
    """
    Execute a terraform command
    """

    command: str = Field(title="terraform command to execute")

    @traceit(name="terraform_exec")
    def __call__(self, *args, **kwargs):
        """
        Execute a terraform command

        :return: The stdout, stderr, and exit code
        """
        return super().__call__(*args, **kwargs)

    @traceit(name="terraform_exec_stream")
    def stream(self, *args, **kwargs):
        return super().stream(*args, **kwargs)


terraform_ctx = Context(
    metadata=Metadata(
        name="terraform",
        labels={"type": "devops"},
        description="Terraform CLI specialist",
    ),
    spec=ContextSpec(
        params={},
        contexts=[os_ctx],
        helpers={
            "terraform_commands": Terraform(),
            "terraform_help": TerraformHelp(),
        },
        executables=[ExecTerraform],
        data="""
You are a terraform CLI specialist.

Here are the available commands to use:
{{ terraform_commands() }}

Here is the help for the terraform CLI:
{{ terraform_help() }}

When you have issue with executing `terraform <subcommand>` try to use `terraform <subcommand> -help` to get more information.
""",
    ),
)
