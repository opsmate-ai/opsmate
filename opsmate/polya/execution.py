from pydantic import BaseModel, Field
from opsmate.dino.types import ToolCall, React, ReactAnswer, Observation
from opsmate.tools.aci import ACITool
from opsmate.tools import ShellCommand
from opsmate.dino.react import react
from typing import Optional, ClassVar
import os
import asyncio
import structlog
import yaml

logger = structlog.get_logger(__name__)


class GithubCloneAndCD(ToolCall):
    """
    Clone a github repository and cd into the directory
    """

    output: str = Field(..., description="The output of the tool call, DO NOT POPULATE")
    github_domain: ClassVar[str] = "github.com"
    github_token: ClassVar[str] = os.getenv("GITHUB_TOKEN")

    repo: str = Field(
        ..., description="The github repository in the format of owner/repo"
    )
    github_token: Optional[str] = Field(
        ...,
        description="The github token to use, DO NOT POPULATE",
        default_factory=lambda: os.getenv("GITHUB_TOKEN"),
    )

    @property
    def clone_url(self) -> str:
        return f"https://{self.github_token}@{self.github_domain}/{self.repo}.git"

    async def __call__(self, *args, **kwargs):
        logger.info("cloning repository", repo=self.repo, domain=self.github_domain)

        try:
            process = await asyncio.create_subprocess_shell(
                f"git clone {self.clone_url}",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            stdout, _ = await asyncio.wait_for(process.communicate(), timeout=60.0)

            # check the exit code
            if process.returncode != 0:
                raise Exception(f"Failed to clone repository: {stdout.decode()}")

            repo_path = self.repo.split("/")[-1]
            logger.info("changing directory", path=repo_path)
            os.chdir(repo_path)

            return stdout.decode()
        except asyncio.TimeoutError:
            return "Failed to clone repository due to timeout"
        except Exception as e:
            return f"Failed to clone repository: {e}"


@react(
    model="claude-3-5-sonnet-20241022",
    tools=[ACITool, ShellCommand, GithubCloneAndCD],
    contexts=["you are an SRE who is tasked to modify the infra as code"],
    tool_calls_per_action=1,
    iterable=True,
)
async def iac_cme(instruction: str):
    """
    You are an SRE who is tasked to modify the infra as code.

    <rule 1>
    Before making any changes, you must read the file(s) to understand:
    * the purpose of the file (e.g. a terraform file deploying IaC, or a yaml file deploying k8s resources)
    * Have a basic understanding of the file's structure
    </rule 1>

    <rule 2>
    Edit must be precise and specific:
    * Tabs and spaces must be used correctly
    * The line range must be specified when you are performing an update operation against a file
    * Stick to the task you are given, don't make drive-by changes
    </rule 2>

    <rule 3>
    After you make the change, you must verify the updated content is correct using the `ACITool.view` or `ACITool.search` commands.
    </rule 3>

    <rule 4>
    NEVER EVER use vi/vim/nano/view or any other text editor to make changes, instead use the `ACITool` tool.
    </rule 4>

    <rule 5>
    Tool usage:
    * `ACITool` tool for file search, view, create, update, append and undo.
    * `ShellCommand` tool for running shell commands that cannot be covered by `ACITool`.
    * `SysChdir` tool for changing the current working directory, DO NOT use `cd` command.
    </rule 5>
    """
    return instruction


async def main():
    instruction = """
Given the facts:

<facts>
fact='The payment service uses readinessProbe and livenessProbe for health checks in its deployment manifest' source='https://github.com/jingkaihe/opsmate-payment-service/blob/main/README.md' weight=8
----------------------------------------------------------------------------------------------------
fact='The health checks are configured to use the /status endpoint instead of conventional /healthz endpoints' source='https://github.com/jingkaihe/opsmate-payment-service/blob/main/README.md' weight=7
----------------------------------------------------------------------------------------------------
fact='The deployment configuration is specified in deploy.yml file' source='https://github.com/jingkaihe/opsmate-payment-service/blob/main/README.md' weight=6
----------------------------------------------------------------------------------------------------
fact='The service is deployed to the payment namespace using kubectl apply -f deploy.yml' source='https://github.com/jingkaihe/opsmate-payment-service/blob/main/README.md' weight=5
----------------------------------------------------------------------------------------------------
fact='The main application code is located in app.py file' source='https://github.com/jingkaihe/opsmate-payment-service/blob/main/README.md' weight=4
----------------------------------------------------------------------------------------------------
</facts>

And the goal:

<goal>
Fix the health check endpoint mismatch in payment-service deployment causing rollout failures
</goal>

Here are the tasks to be performed **ONLY**:

<tasks>
* Clone the opsmate-payment-service repository
* Create a new git branch named 'opsmate-fix-health-probe-path-001'
* Locate and review the deploy.yml file in the repository
* Update the readiness and liveness probe configurations in deploy.yml to use '/status' instead of '/health'
* Commit and push the changes to the repository
</tasks>
"""
    async for result in await iac_cme(instruction):
        if isinstance(result, React):
            print(
                f"""
## action
{result.action}

## thoughts
{result.thoughts}
                """
            )
        elif isinstance(result, Observation):
            print(
                f"""
## observation
{result.observation}

## tool outputs
{yaml.dump([tool.model_dump() for tool in result.tool_outputs])}
"""
            )
        elif isinstance(result, ReactAnswer):
            print(
                f"""
{result.answer}
"""
            )


if __name__ == "__main__":
    asyncio.run(main())
