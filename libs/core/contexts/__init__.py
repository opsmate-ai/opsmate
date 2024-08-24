from libs.core.types import Context, ContextSpec, Metadata
from pydantic import Field
from typing import Tuple


def current_os():
    import platform

    return platform.system()


def exec_shell(command: str) -> Tuple[str, str, int]:
    """
    Execute a shell script
    :param command: The shell command to execute

    :return: The stdout, stderr, and exit code
    """

    import subprocess

    process = subprocess.Popen(
        command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )

    stdout, stderr = process.communicate()
    return str(stdout), str(stderr), process.returncode


built_in_helpers = {
    "get_current_os": current_os,
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
        executables=[exec_shell],
        data="you are a sysadmin specialised in OS commands",
    ),
)
