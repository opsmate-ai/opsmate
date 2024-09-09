from libs.core.types import *
from libs.core.contexts import built_in_helpers
import jinja2


def render_context(context: Context):
    env = jinja2.Environment()
    for helper_name, helper in built_in_helpers.items():
        env.globals[helper_name] = helper

    output = ""
    for sub_ctx in context.spec.contexts:
        output += render_context(sub_ctx) + "\n"

    template = env.from_string(context.spec.data)

    return output + template.render()
