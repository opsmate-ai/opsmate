from libs.core.types import Context, ContextSpec, Executable, Metadata
from pydantic import Field
from typing import Tuple


class CurrentOS(Executable):
    """
    Get the current OS
    """

    def execute(self, ask: bool = False) -> str:
        import platform

        return platform.system()


class Exec(Executable):
    """
    Execute a shell script returns the stdout and stderr and the exit code as a tuple
    """

    command: str = Field(title="command")

    def execute(self, ask: bool = False) -> Tuple[str, str, int]:
        """
        Execute a shell script

        Args:
            command (str): The shell command to execute

        Returns:
            tuple: The stdout, stderr, and exit code
        """
        import subprocess

        if ask:
            ans = input(f"Are you sure you want to run {self.command}? (y/n): ")
            if ans.lower() != "y":
                return "", "User cancelled the operation", 127

        process = subprocess.Popen(
            self.command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )

        stdout, stderr = process.communicate()
        return str(stdout), str(stderr), process.returncode


built_in_helpers = {
    "get_current_os": CurrentOS().execute,
}


os_ctx = Context(
    metadata=Metadata(
        name="os",
        apiVersion="v1",
        labels={"type": "system"},
        description="System tools",
    ),
    spec=ContextSpec(
        tools=[], data="you are currently running on {{ get_current_os() }}"
    ),
)

cli_ctx = Context(
    metadata=Metadata(
        name="cli",
        apiVersion="v1",
        labels={"type": "system"},
        description="System CLI",
    ),
    spec=ContextSpec(
        params={},
        contexts=[os_ctx],
        executables=[Exec],
        data="you are a sysadmin specialised in OS commands",
    ),
)
