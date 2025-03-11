from opsmate.dino.types import React, ReactAnswer, Observation, Message
from opsmate.tools import ShellCommand, ACITool, GithubCloneAndCD, GithubRaisePR
from opsmate.tools.system import SysChdir
from opsmate.dino.react import react
from typing import List
import asyncio
import structlog
import yaml

logger = structlog.get_logger(__name__)


iac_sme_context = """
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
Tool usage:
* `ACITool` tool for file search, view, create, update, append and undo.
* `ShellCommand` tool for running shell commands that cannot be covered by `ACITool`, in other words, **DO NOT** use `ShellCommand` to run `view/vim/emacs/nano/vi` commands.
* `GithubCloneAndCD` tool for cloning a github repository and changing the current working directory to the repository, **DO NOT use `gh` command**.
* `GithubRaisePR` tool for raising a PR to the github repository, **DO NOT use `gh` command**.
* `SysChdir` tool for changing the current working directory, **DO NOT** use `cd` command.
</rule 4>
"""


@react(
    model="claude-3-5-sonnet-20241022",
    tools=[ACITool, ShellCommand, GithubCloneAndCD, GithubRaisePR, SysChdir],
    contexts=[iac_sme_context],
    tool_calls_per_action=1,
    max_iter=20,
    iterable=True,
)
async def iac_sme(instruction: str, chat_history: List[Message] = []):
    """
    You are an SRE who is tasked to modify the infra as code.
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
* Raise a PR for the changes
</tasks>
"""
    async for result in await iac_sme(instruction):
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
