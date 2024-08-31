from libs.core.types import Context, ContextSpec, Metadata, Executable
from pydantic import Field, BaseModel


class CurrentOS(Executable):
    def __call__(self, *args, **kwargs):
        import platform

        return platform.system()


class ExecShellOutput(BaseModel):
    stdout: str = Field(title="stdout")
    stderr: str = Field(title="stderr")
    exit_code: int = Field(title="exit_code")


class ExecShell(Executable):
    command: str = Field(title="command to execute")

    def __call__(
        self,
        ask: bool = False,
    ) -> ExecShellOutput:
        """
        Execute a shell script

        :return: The stdout, stderr, and exit code
        """

        import subprocess

        print("executing shell command: ", self.command)
        if ask:
            if input("Proceed? (yes/no): ").strip().lower() != "yes":
                return ExecShellOutput(
                    stdout="", stderr="Execution cancelled by user", exit_code=1
                )

        process = subprocess.Popen(
            self.command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )

        stdout, stderr = process.communicate()
        return ExecShellOutput(
            stdout=str(stdout), stderr=str(stderr), exit_code=process.returncode
        )


built_in_helpers = {
    "get_current_os": CurrentOS(),
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
        executables=[ExecShell],
        data="you are a sysadmin specialised in OS commands",
    ),
)

react_prompt = """
You run in a loop of thought, actions.
At the end of the loop you output an answer.
Use thought to describe your thoughts about the question you have been asked.
Use actions to run one of the actions available to you - then return.

If you know the answer you can skip the Thought and Actions steps, and output the Answer directly.

Notes you output must be in format as follows:

<output>
question: ...
thought: ...
actions: ...
</output>

Or

<output>
answer: ...
</output>

Example:

user asks: what is the process that is hogging the cpus?

your output:

<output>
question: what is the process that is hogging the cpus?
thought: To identify the process consuming the most CPU resources, I should analyze the system's current resource usage statistics.
action: Execute the 'top' command to see a real-time view of CPU usage and identify which process is currently consuming the most CPU resources.
</output>

In userspace `top -b -n 1 | head -n 20` is executed and you were given

<observation>
stdout: top - 21:35:47 up 3 days,  6:06,  5 users,  load average: 1.96, 1.07, 0.44
Tasks: 190 total,   3 running, 187 sleeping,   0 stopped,   0 zombie
%Cpu(s): 25.3 us,  1.1 sy,  0.0 ni, 73.6 id,  0.0 wa,  0.0 hi,  0.0 si,  0.0 st
MiB Mem :  32090.2 total,  27269.1 free,   2050.1 used,   3240.9 buff/cache
MiB Swap:      0.0 total,      0.0 free,      0.0 used.  30040.1 avail Mem

    PID USER      PR  NI    VIRT    RES    SHR S  %CPU  %MEM     TIME+ COMMAND
  42717 ubuntu    20   0    3624    384    384 R 100.0   0.0   3:16.56 stress
...
</observation>

you output:

<output>
thought: "The 'stress' process is currently consuming 100% of the CPU resources."
action: "I will kill the 'stress' process with the PID 42717 to free up CPU resources."
</output>

In user space `kill -TERM 42717` is executed and you were given the output:

<observation>
stdout: ""
stderr: ""
exit_code: 0
</observation>

You answer:

<output>
I have killed the 'stress' process with PID 42717.
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
        data=react_prompt,
    ),
)
