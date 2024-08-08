from libs.core.types import *
from typing import Callable, Dict, List, Union
from libs.core.contexts import built_in_helpers
from openai import Client
import instructor
import jinja2


def render_context(context: Context, helpers: Dict[str, Callable] = {}):
    env = jinja2.Environment()
    for helper_name, helper in built_in_helpers.items():
        env.globals[helper_name] = helper
    for helper_name, helper in helpers.items():
        env.globals[helper_name] = helper

    output = ""
    for sub_ctx in context.spec.contexts:
        output += render_context(sub_ctx, helpers) + "\n"

    template = env.from_string(context.spec.data)

    return output + template.render()


def exec_task(client: Client, task: Task):
    instructor_client = instructor.from_openai(client)

    prompt = ""
    for ctx in task.spec.contexts:
        prompt += render_context(ctx) + "\n"

    prompt += "\nhere is the task instruction: \n"
    prompt += task.spec.instruction

    executables: List[Executable] = []
    for ctx in task.spec.contexts:
        executables.extend(list(ctx.all_executables()))

    if len(executables) == 0:
        instructor_client.mode = instructor.Mode.PARALLEL_TOOLS
    else:
        instructor_client.mode = instructor.Mode.TOOLS

    resp = instructor_client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": prompt,
            },
        ],
        model="gpt-4o",
        response_model=Iterable[Union[tuple(executables)]],
    )

    for fc in resp:
        print(fc.command)
