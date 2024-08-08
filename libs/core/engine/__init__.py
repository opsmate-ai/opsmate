from libs.core.types import *
from typing import Callable, Dict, List, Union
from libs.core.contexts import built_in_helpers
from openai import Client
import instructor
import jinja2
import json


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

    if len(executables) != 0:
        instructor_client = instructor.from_openai(
            client, mode=instructor.Mode.PARALLEL_TOOLS
        )

    messages = [
        {"role": "user", "content": prompt},
    ]

    resp_msg, resp = instructor_client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        response_model=Iterable[Union[tuple(executables)]],
    )

    messages.append(resp_msg)

    for resp_item in resp:
        tool_call_id, tool = resp_item
        tool_output = tool.execute()
        messages.append(
            {
                "role": "tool",
                "content": json.dumps(tool_output),
                "tool_call_id": tool_call_id,
            },
        )

    instructor_client = instructor.from_openai(client)
    resp = instructor_client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        response_model=task.spec.response_model,
    )

    return resp
