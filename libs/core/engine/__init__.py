from libs.core.types import *
from typing import Callable, Dict, List, Union
from libs.core.contexts import built_in_helpers
from openai import Client
import jinja2
import json
from pydantic import create_model
import inspect, json
from inspect import Parameter


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


def schema(f):
    kw = {
        n: (o.annotation, ... if o.default == Parameter.empty else o.default)
        for n, o in inspect.signature(f).parameters.items()
    }
    s = create_model(f"Input for `{f.__name__}`", **kw).schema()
    s["additionalProperties"] = False
    return {
        "type": "function",
        "function": dict(
            name=f.__name__, description=f.__doc__, strict=True, parameters=s
        ),
    }


def exec_task(client: Client, task: Task, ask: bool = False):
    prompt = ""
    for ctx in task.spec.contexts:
        prompt += render_context(ctx) + "\n"

    prompt += "\nhere is the task instruction: \n"
    prompt += task.spec.instruction

    executables: Dict[str, Callable] = {}
    # for ctx in task.spec.contexts:
    #     executables.extend(list(ctx.all_executables()))

    for ctx in task.spec.contexts:
        for executable in ctx.all_executables():
            executables[executable.__name__] = executable

    messages = [
        {"role": "user", "content": prompt},
    ]

    # resp_msg, resp = instructor_client.chat.completions.create(
    #     model="gpt-4o",
    #     messages=messages,
    #     response_model=Iterable[Union[tuple(executables)]],
    # )
    tools = [schema(f) for f in executables.values()]

    completion = client.beta.chat.completions.parse(
        model="gpt-4o-2024-08-06",
        messages=messages,
        tools=tools,
        response_format=task.spec.response_model,
    )

    if completion.choices[0].message.tool_calls is not None:
        messages.append(completion.choices[0].message)
        for tool_call in completion.choices[0].message.tool_calls:
            tool_name = tool_call.function.name
            tool = executables[tool_name]
            tool_call_id = tool_call.id
            messages.append(
                {
                    "role": "tool",
                    "content": json.dumps(tool(**tool_call.function.parsed_arguments)),
                    "tool_call_id": tool_call_id,
                },
            )

    completion = client.beta.chat.completions.parse(
        model="gpt-4o-2024-08-06",
        messages=messages,
        tools=tools,
        response_format=task.spec.response_model,
    )

    resp = completion.choices[0].message.parsed

    return resp
