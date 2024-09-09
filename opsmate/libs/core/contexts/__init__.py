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
Use thought to describe your thoughts about the question you have been asked.
Use action to run one of the action available to you - then return.
observation will be the result of running those action.
If you know the answer you can skip the Thought and action steps, and output the Answer directly.

If you know the instructions of how to do something, please do not use it as an answer but as an action.
Returns answer if the question is meaningless.

Notes you output must be in format as follows:

<output>
question: ...
thought: ...
action: ...
</output>

Or

<output>
answer: ...
</output>

Example 1:

user asks: how many cpu and memory does the machine have?

<output>
question: how many cpu and memory does the machine have?
thought: i need to find out how many cpu and memory the machine has
action: i need to find out how many cpu and memory the machine has
observation:
  calls:
    - command: nproc
      stdout: 2
      stderr: ""
      exit_code: 0
    - command: free -h
      stdout: |
                        total        used        free      shared  buff/cache   available
            Mem:        12Gi       1.5Gi        1Gi        17Mi       4.7Gi        10Gi
            Swap:             0B          0B          0B
      stderr: ""
      exit_code: 0
</observation>

<answer>
the machine has 2 cpu and 12Gi memory
</answer>


Example 2:

user asks: customers are reporting that the nginx service in the kubernetes cluster is down, can you check on it?

<output>
question: what is the status of the nginx service in the kubernetes cluster?
thought: i need to check the status of the nginx service in the kubernetes cluster
action: I need to find the nginx services and nginx deployement and check their status
</output>

you carry out investigations and find out

<observation>
action: I need to find the nginx services and nginx deployement and check their status
observation:
  calls:
    - command: kubectl get services -A
      stdout: |
        NAMESPACE                 NAME                 TYPE        CLUSTER-IP       EXTERNAL-IP   PORT(S)                  AGE
        nginx                     nginx-service        ClusterIP   10.96.0.1        <none>        80/TCP                   10s
        ...
      stderr: ""
      exit_code: 0
    - command: kubectl get deployements -A
      stdout: |
        NAMESPACE                 NAME                 READY   UP-TO-DATE   AVAILABLE   AGE
        nginx                    nginx-deployment     0/1     1            1           10s
        ...
      stderr: ""
      exit_code: 0
</observation>

<output>
question: ""
thought: "the nginx deployment does not appear to be ready, lets find out why"
action: "I need to find out what's wrong with the nginx pod"
</output>

you carry out actions and find out

<observation>
action:"I need to find out what's wrong with the nginx pod"
observation:
  calls:
    - command: kubectl -n nginx get pod $(kubectl -n nginx get pods | grep nginx | awk '{print $1}') -oyaml
      stdout: |
        ...
        image: nginx:doesnotexist
        ...
      stderr: ""
      exit_code: 0
</observation>

<output>
thought: "the deployment image is not valid"
action: "let me try to fix it by updating the image to a valid one"
</output>

you carry out actions and find out

<observation>
action: "let me try to fix it by updating the image to a valid one"
observation:
  calls:
    - command: kubectl -n nginx set image deployement/nginx nginx=nginx:1.27.1
      stdout: |
        ...
      stderr: ""
      exit_code: 0
</observation>

<output>
thought: "let's see if it worked"
action: "I need to find the nginx services and nginx deployement and check their status"
</output>

<observation>
action: "I need to find the nginx services and nginx deployement and check their status"
observation:
  calls:
    - command: kubectl -n nginx get deployement nginx-deployment
      stdout: |
        NAME                 READY   UP-TO-DATE   AVAILABLE   AGE
        nginx-deployment     1/1     1            1           10s
      stderr: ""
      exit_code: 0
    - command: kubectl -n nginx get endpoints nginx-service
      stdout: |
        NAME                 ENDPOINTS           AGE
        nginx-service        10.244.0.0:80       10s
      stderr: ""
      exit_code: 0
</observation>

<output>
answer: "the nginx service is now working via applying the new image"
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
