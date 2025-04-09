from opsmate.tools import (
    ShellCommand,
    KnowledgeRetrieval,
    ACITool,
    HtmlToText,
    Thinking,
)
from opsmate.dino.context import context
from opsmate.runtime import Runtime


@context(
    name="terraform",
    tools=[
        ShellCommand,
        KnowledgeRetrieval,
        ACITool,
        HtmlToText,
        Thinking,
    ],
)
async def terraform_ctx(runtime: Runtime) -> str:
    """Terraform SME"""

    return f"""
<assistant>
You are a world class SRE who is an expert in terraform. You are tasked to help with terraform related problem solving
</assistant>

<available_terraform_options>
{await __terraform_help(runtime)}
</available_terraform_options>

<important>
When you have issue with executing `terraform <subcommand>` try to use `terraform <subcommand> -help` to get more information.
</important>
    """


async def __terraform_help(runtimes: dict[str, Runtime]) -> str:
    return await runtimes["ShellCommand"].run("terraform -help")
