from libs.core.types import *
from typing import Dict, List, Union
from libs.core.contexts import built_in_helpers, react_ctx
from openai import Client
import jinja2
import json
from pydantic import create_model
import inspect, json
from inspect import Parameter


def render_context(context: Context, helpers: Dict[str, ToolCallable] = {}):
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

    executables: Dict[str, ToolCallable] = {}
    for ctx in task.spec.contexts:
        for executable in ctx.all_executables():
            executables[executable.__name__] = executable

    messages = [
        {"role": "user", "content": prompt},
    ]

    tools = [schema(f) for f in executables.values()]

    completion = client.beta.chat.completions.parse(
        model="gpt-4o-2024-08-06",
        messages=messages,
        tools=tools,
        response_format=task.spec.response_model,
    )

    tool_calls = completion.choices[0].message.tool_calls
    if len(tool_calls) > 0:
        messages.append(completion.choices[0].message)
        for tool_call in tool_calls:
            tool_name = tool_call.function.name
            tool = executables[tool_name]
            tool_call_id = tool_call.id

            result: BaseModel = tool(**tool_call.function.parsed_arguments)

            messages.append(
                {
                    "role": "tool",
                    "content": result.model_dump_json(),
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


def exec_react_task(client: Client, task: Task, ask: bool = False):
    if task.spec.response_model != ReactOutput:
        raise ValueError("Task response model must be ReactOutput")

    if react_ctx not in task.spec.contexts:
        raise ValueError("React context is required for react task")

    prompt = ""
    for ctx in task.spec.contexts:
        prompt += render_context(ctx) + "\n"

    prompt += "\nhere is the task instruction: \n"
    prompt += task.spec.instruction

    executables: Dict[str, ToolCallable] = {}
    for ctx in task.spec.contexts:
        for executable in ctx.all_executables():
            executables[executable.__name__] = executable

    messages = [
        {"role": "user", "content": prompt},
    ]

    tools = [schema(f) for f in executables.values()]

    while True:
        completion = client.beta.chat.completions.parse(
            model="gpt-4o-2024-08-06",
            messages=messages,
            tools=tools,
            response_format=ReactOutput,
        )

        parsed = completion.choices[0].message.parsed

        if parsed is not None:
            if parsed.answer is not None:
                return parsed.answer

            if parsed.observation is not None:
                print("observation: ", parsed.observation)
                messages.append(
                    {"role": "user", "content": "observation: " + parsed.observation}
                )

            if parsed.thought is not None:
                print("thought: ", parsed.thought)
                messages.append(
                    {"role": "user", "content": "thought: " + parsed.thought}
                )

        tool_calls = completion.choices[0].message.tool_calls
        if len(tool_calls) > 0:
            messages.append(completion.choices[0].message)
            for tool_call in tool_calls:
                tool_name = tool_call.function.name
                tool = executables[tool_name]
                tool_call_id = tool_call.id

                result: BaseModel = tool(**tool_call.function.parsed_arguments)

                messages.append(
                    {
                        "role": "tool",
                        "content": result.model_dump_json(),
                        "tool_call_id": tool_call_id,
                    },
                )

    # completion = client.beta.chat.completions.parse(
    #     model="gpt-4o-2024-08-06",
    #     messages=messages,
    #     tools=tools,
    #     response_format=task.spec.response_model,
    # )

    # resp = completion.choices[0].message.parsed

    # return resp
