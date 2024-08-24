from libs.core.types import Context, ContextSpec, Metadata
from pydantic import Field, BaseModel
from typing import Tuple


def current_os():
    import platform

    return platform.system()


class ExecShellOutput(BaseModel):
    stdout: str = Field(title="stdout")
    stderr: str = Field(title="stderr")
    exit_code: int = Field(title="exit_code")


def exec_shell(command: str) -> ExecShellOutput:
    """
    Execute a shell script
    :param command: The shell command to execute

    :return: The stdout, stderr, and exit code
    """

    import subprocess

    print("executing shell command: ", command)

    process = subprocess.Popen(
        command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )

    stdout, stderr = process.communicate()
    # return str(stdout), str(stderr), process.returncode
    return ExecShellOutput(
        stdout=str(stdout), stderr=str(stderr), exit_code=process.returncode
    )


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

react_prompt = """
You run in a loop of thought, actions, observation.
At the end of the loop you output an answer.
Use thought to describe your thoughts about the question you have been asked.
Use actions to run one of the actions available to you - then return.
observation will be the result of running those actions.

If you know the answer you can skip the Thought and Actions steps, and output the Answer directly.

Notes you output must be in format as follows:

<output>
question: ...
thought: ...
actions: ...
</output>

Or

<output>
observation: ...
question: ...
thought: ...
actions: ...
</output>

Or

<output>
answer: ...
</output>
"""

react_ctx = Context(
    metadata=Metadata(
        name="react",
        apiVersion="v1",
        labels={"type": "system"},
        description="System React",
    ),
    spec=ContextSpec(
        params={},
        contexts=[cli_ctx],
        data=react_prompt,
    ),
)
