from opsmate.tools import (
    ShellCommand,
    KnowledgeRetrieval,
    ACITool,
    HtmlToText,
    PrometheusTool,
)
from opsmate.dino.context import context
from opsmate.runtime import Runtime


@context(
    name="cli",
    tools=[
        ShellCommand,
        KnowledgeRetrieval,
        ACITool,
        HtmlToText,
        PrometheusTool,
    ],
)
async def cli_ctx(runtime: Runtime) -> str:
    """System Admin Assistant"""

    return f"""
  <assistant>
  You are a world class SRE who is good at solving problems. You are given access to the terminal for solving problems.
  </assistant>

  <sys-info>
    <os-info>
    {await runtime.os_info()}
    </os-info>
    <whoami>
    {await runtime.whoami()}
    </whoami>
    <runtime-info>
    {await runtime.runtime_info()}
    </runtime-info>
    <has-systemd>
    {await runtime.has_systemd()}
    </has-systemd>
  </sys-info>

  <important>
  - If you anticipate the command will generates a lot of output, you should limit the output via piping it to `tail -n 100` command or grepping it with a specific pattern.
  - Do not run any command that runs in interactive mode.
  - Do not run any command that requires manual intervention.
  - Do not run any command that requires user input.
  </important>
    """
