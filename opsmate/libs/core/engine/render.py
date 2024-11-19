from opsmate.libs.core.types import *
from opsmate.libs.core.contexts import built_in_helpers
import jinja2


def render_context(context: Context):
    env = jinja2.Environment()
    for helper_name, helper in built_in_helpers.items():
        env.globals[helper_name] = helper

    for helper_name, helper in context.spec.helpers.items():
        env.globals[helper_name] = helper

    output = ""
    for sub_ctx in context.spec.contexts:
        output += render_context(sub_ctx) + "\n"

    template = env.from_string(context.spec.data)

    return output + template.render()


def render_tools(task: Task):
    executables = task.all_executables

    return f"""
Here are the available tools you can use:
<tools>
{_render_tools(executables)}
</tools>
"""


def _render_tools(executables: list[Type[Executable]]):
    kv = {}
    for executable in executables:
        kv[executable.__name__] = executable.__doc__
    return yaml.dump(kv)
