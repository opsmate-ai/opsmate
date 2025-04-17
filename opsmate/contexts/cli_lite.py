from opsmate.tools import (
    ShellCommand,
)
from opsmate.dino.context import context
from opsmate.runtime import Runtime
from jinja2 import Template


@context(
    name="cli-lite",
    tools=[ShellCommand],
)
async def cli_lite_ctx(runtimes: dict[str, Runtime] = {}) -> str:
    """System Admin Assistant running on small LLM"""

    # Pre-fetch all runtime information asynchronously
    runtime_info = {}
    for runtime_name, runtime in runtimes.items():
        runtime_info[runtime_name] = {
            "os_info": await runtime.os_info(),
            "whoami": await runtime.whoami(),
        }

    template = Template(
        """
  <assistant>
  You are a world class SRE who is good at solving problems. You are given access to the terminal for solving problems.
  </assistant>

  You have access to the following runtimes:

  <sys-info>
    {% for runtime_name, info in runtime_info.items() %}
    <runtime name="{{ runtime_name }}">
      <whoami>
      {{ info.whoami }}
      </whoami>
      <os-info>
      {{ info.os_info }}
      </os-info>
    </runtime>
    {% endfor %}
  </sys-info>

    """
    )

    rendered_template = template.render(runtime_info=runtime_info)
    return rendered_template
