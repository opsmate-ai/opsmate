from opsmate.libs.core.types import (
    Context,
    ContextSpec,
    Metadata,
    Executable,
    ShellExecOutput,
    SearchOutput,
)
from opsmate.libs.knowledge import get_runbooks_table, Runbook
from pydantic import Field
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

    @property
    def streamable(self):
        return True

    @traceit(name="exec_shell")
    def __call__(
        self,
        ask: bool = False,
        stream: bool = False,
        span: Span = None,
    ):
        """
        Execute a shell script

        Example Usage:

        ```
        ExecShell:
            command: ls -l /etc/os-release
        ```

        :return: The stdout, stderr, and exit code
        """

        span.set_attribute("command", self.command)

        import subprocess

        logger.info("ExecShell", command=self.command)
        if ask:
            if input("Proceed? (yes/no): ").strip().lower() != "yes":
                return ShellExecOutput(
                    command=self.command,
                    stdout="",
                    stderr="Execution cancelled by user",
                    exit_code=1,
                )

        process = subprocess.Popen(
            self.command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )

        stdout, stderr = process.communicate()

        logger.info(
            "ExecShell.result",
            command=self.command,
            stdout=stdout.decode().strip(),
            stderr=stderr.decode().strip(),
            exit_code=process.returncode,
        )

        return ShellExecOutput(
            command=self.command,
            stdout=stdout.decode().strip(),
            stderr=stderr.decode().strip(),
            exit_code=process.returncode,
        )

    @traceit(name="exec_shell_stream")
    def stream(
        self,
        ask: bool = False,
        span: Span = None,
    ) -> Generator[dict, None, None]:
        """
        Execute a shell script

        :return: generator of ExecOutput
        """

        span.set_attribute("command", self.command)

        import subprocess

        logger.info("ExecShell", command=self.command)
        if ask:
            if input("Proceed? (yes/no): ").strip().lower() != "yes":
                return ShellExecOutput(
                    command=self.command,
                    stdout="",
                    stderr="Execution cancelled by user",
                    exit_code=1,
                )

        process = subprocess.Popen(
            self.command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
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
                yield ShellExecOutput(
                    command=self.command,
                    stdout=out.decode().strip(),
                    stderr="",
                    exit_code=-1,
                )
            except queue.Empty:
                pass

            try:
                err = stderr_queue.get_nowait()
                stderr += err
                yield ShellExecOutput(
                    command=self.command,
                    stdout="",
                    stderr=err.decode().strip(),
                    exit_code=-1,
                )
            except queue.Empty:
                pass

        stdout_thread.join()
        stderr_thread.join()

        process.wait()

        yield ShellExecOutput(
            command=self.command,
            stdout=stdout.decode().strip(),
            stderr=stderr.decode().strip(),
            exit_code=process.returncode,
        )


class KnowledgeBaseQuery(Executable):
    """
    Query the knowledge base

    Example Usage:

    ```
    KnowledgeBaseQuery:
        query: how does dirty write back work on Linux?
    ```

    """

    query: str = Field(title="question to ask")

    @property
    def streamable(self):
        return False

    @traceit(name="knowledge_query")
    def __call__(
        self,
        ask: bool = False,
        span: Span = None,
        limit: int = 3,
    ):
        span.set_attribute("query", self.query)

        runbooks = (
            get_runbooks_table().search(self.query).limit(limit).to_pydantic(Runbook)
        )

        results = [
            {
                "filename": runbook.filename,
                "content": runbook.content,
            }
            for runbook in runbooks
        ]
        span.set_attributes(
            {
                "results.length": len(runbooks),
                "results": results,
            }
        )
        return SearchOutput(results=results)


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

kb_ctx = Context(
    metadata=Metadata(
        name="knowledgebase-query",
        labels={"type": "system"},
        description="Knowledge Base Query",
    ),
    spec=ContextSpec(
        params={},
        executables=[KnowledgeBaseQuery],
        data="""
You can query the knowledge base for information.
        """,
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
        contexts=[os_ctx, kb_ctx],
        executables=[ExecShell],
        data="""
        you are a sysadmin specialised in sysadmin task and problem solving.
        """,
    ),
)

react_prompt = """
You run in a loop of question, thought, action.
At the end of the loop you output an answer.
Use "Question" to describe the question you have been asked.
Use "Thought" to describe your thoughts about the question you have been asked.
Use "Action" to describe the action items you are going to take. action can be the question if the question is easy enough
"Observation" is the result of running those action.

Notes you output must be in format as follows:

<react>
thought: ...
action: ...
</react>

Or

<react>
answer: ...
</react>

When you know how to do something, provide the steps as an action rather than giving them as an answer. For example:

BAD EXAMPLE:
<react>
answer: To get the operating system name, use `cat /etc/os-release`
</react>

GOOD EXAMPLE:
<react>
thought: I can find the operating system name in the os-release file
action: run `cat /etc/os-release`
</react>

Example 1:

user asks: how many cpu and memory does the machine have?

<react>
question: how many cpu and memory does the machine have?
thought: i need to find out how many cpu and memory the machine has
action: runs `lscpu` and `free -m` to find out
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
action: runs `kubectl get svc,deploy -n nginx` to check the status of the nginx service and nginx deployment
</react>

you carry out investigations and find out

<observation>
nginx service is up and running just fine, the deployment is not ready
</observation>

<react>
thought: the nginx deployment does not appear to be ready, lets find out why
action: runs `kubectl describe deploy nginx -n nginx` to find out what's wrong with the nginx pod
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
