from opsmate.tools.aci import ACITool
from opsmate.tools import ShellCommand
from opsmate.tools.system import SysChdir
from opsmate.dino.react import react
from opsmate.dino.types import React, Observation, ReactAnswer
import asyncio
import yaml


@react(
    model="claude-3-5-sonnet-20241022",
    tools=[ACITool, ShellCommand, SysChdir],
    contexts=["you are an SRE who is tasked to modify the infra as code"],
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
    Never ever use vim or any other text editor to make changes, instead use the `ACITool` tool.
    </rule 4>

    <rule 5>
    Tool usage:
    * `ACITool` for file search, view, create, update, append and undo.
    * `ShellCommand` for running shell commands that cannot be covered by `ACITool`.
    * `SysChdir` for changing the current working directory
    </rule 5>
    """
    return instruction


async def main():
    plan = [
        "git clone git@github.com:jingkaihe/opsmate-payment-service.git",
        "cd opsmate-payment-service",
        "branch out to a new branch called `health-check-fix-` with a random number suffix",
        "change the k8s health check path to `/status`",
        "commit the changes",
        "push the changes to the remote repo",
    ]

    plan_to_md = "\n".join(f"* {step}" for step in plan)

    async for result in await iac_cme(
        plan_to_md,
        model="gpt-4o",
    ):
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
