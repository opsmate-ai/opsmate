from opsmate.libs.core.types import (
    Context,
    ContextSpec,
    Metadata,
    Executable,
    ExecOutput,
)
from pydantic import Field, BaseModel
from opsmate.libs.core.trace import traceit
from opentelemetry.trace import Span
from typing import Generator
import structlog

logger = structlog.get_logger()


class CurrentOS(Executable):
    def __call__(self, *args, **kwargs):
        import platform

        return platform.system()


class ExecShell(Executable):
    """
    Execute a shell script
    """

    command: str = Field(title="command to execute")

    @traceit(name="exec_shell")
    def __call__(
        self,
        ask: bool = False,
        stream: bool = False,
        span: Span = None,
    ) -> ExecOutput | Generator[ExecOutput, None, None]:
        """
        Execute a shell script

        :return: The stdout, stderr, and exit code
        """

        span.set_attribute("command", self.command)

        import subprocess

        logger.info("ExecShell", command=self.command)
        if ask:
            if input("Proceed? (yes/no): ").strip().lower() != "yes":
                return ExecOutput(
                    stdout="", stderr="Execution cancelled by user", exit_code=1
                )

        process = subprocess.Popen(
            self.command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )

        if not stream:
            stdout, stderr = process.communicate()

            logger.info(
                "ExecShell.result",
                stdout=stdout.decode().strip(),
                stderr=stderr.decode().strip(),
                exit_code=process.returncode,
            )

            return ExecOutput(
                stdout=stdout.decode().strip(),
                stderr=stderr.decode().strip(),
                exit_code=process.returncode,
            )

        import threading
        import queue

        stdout_queue = queue.Queue()
        stderr_queue = queue.Queue()

        def read_stdout():
            for out in process.stdout:
                stdout_queue.put(out)

        def read_stderr():
            for err in process.stderr:
                stderr_queue.put(err)

        stdout_thread = threading.Thread(target=read_stdout)
        stderr_thread = threading.Thread(target=read_stderr)

        stdout_thread.start()
        stderr_thread.start()

        stdout = b""
        stderr = b""

        while (
            stdout_thread.is_alive()
            or stderr_thread.is_alive()
            or not stdout_queue.empty()
            or not stderr_queue.empty()
        ):
            try:
                out = stdout_queue.get_nowait()
                stdout += out
                yield ExecOutput(
                    stdout=out.decode().strip(),
                    stderr="",
                    exit_code=-1,
                )
            except queue.Empty:
                pass

            try:
                err = stderr_queue.get_nowait()
                stderr += err
                yield ExecOutput(
                    stdout="",
                    stderr=err.decode().strip(),
                    exit_code=-1,
                )
            except queue.Empty:
                pass

        stdout_thread.join()
        stderr_thread.join()

        process.wait()

        yield ExecOutput(
            stdout=stdout.decode().strip(),
            stderr=stderr.decode().strip(),
            exit_code=process.returncode,
        )


built_in_helpers = {
    "get_current_os": CurrentOS(),
}


os_ctx = Context(
    metadata=Metadata(
        name="os",
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
        labels={"type": "system"},
        description="System CLI",
    ),
    spec=ContextSpec(
        params={},
        contexts=[os_ctx],
        executables=[ExecShell],
        data="""
        you are a sysadmin specialised in OS commands.

        a few things to bare in mind:
        - do not run any command that are unethical or harmful
        - do not run any command that runs in interactive mode
        """,
    ),
)

react_prompt = """
You run in a loop of thought, action.
At the end of the loop you output an answer.
Use "Thought" to describe your thoughts about the question you have been asked.
Use "Action" to describe the action items you are going to take. action can be the question if the question is easy enough
observation will be the result of running those action.
If you know the answer you can skip the Thought and action steps, and output the Answer directly.

If you know the instructions of how to do something, please do not use it as an answer but as an action.
Returns answer if the question is meaningless.

Notes you output must be in format as follows:

<react>
question: ...
thought: ...
action: ...
</react>

Or

<react>
answer: ...
</react>

Example 1:

user asks: how many cpu and memory does the machine have?

<react>
question: how many cpu and memory does the machine have?
thought: i need to find out how many cpu and memory the machine has
action: i need to find out how many cpu and memory the machine has
</react>

<observation>
cpu: 2 vcpu
memory: 12Gi
</observation>

<answer>
the machine has 2 cpu and 12Gi memory
</answer>

Example 2:

user asks: customers are reporting that the nginx service in the kubernetes cluster is down, can you check on it?

<react>
question: what is the status of the nginx service in the kubernetes cluster?
thought: i need to check the status of the nginx service in the kubernetes cluster
action: I need to find the nginx services and nginx deployement and check their status
</react>

you carry out investigations and find out

<observation>
nginx service is up and running just fine, the deployment is not ready
</observation>

<react>
question: ""
thought: "the nginx deployment does not appear to be ready, lets find out why"
action: "I need to find out what's wrong with the nginx pod"
</react>

you carry out actions and find out

<observation>
the image is `image: nginx:doesnotexist` which does not exist
</observation>

You can then give the answer:

<answer>
the nginx service is now working via applying the new image
</answer>
"""

react_ctx = Context(
    metadata=Metadata(
        name="react",
        labels={"type": "system"},
        description="System React",
    ),
    spec=ContextSpec(
        params={},
        data=react_prompt,
    ),
)
