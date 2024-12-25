from typing import List
from opsmate.dino.types import ToolCall
from opsmate.tools.command_line import ShellCommand
import subprocess


def terraform_ctx() -> str:
    return f"""
<assistant>
You are a world class SRE who is an expert in terraform. You are tasked to help with terraform related problem solving
</assistant>

<available_terraform_options>
{__terraform_help()}
</available_terraform_options>

<important>
When you have issue with executing `terraform <subcommand>` try to use `terraform <subcommand> -help` to get more information.
</important>
    """


def terraform_tools() -> List[ToolCall]:
    return [
        ShellCommand,
    ]


def __terraform_help() -> str:
    output = subprocess.run(["terraform", "-help"], capture_output=True)
    return output.stdout.decode()
