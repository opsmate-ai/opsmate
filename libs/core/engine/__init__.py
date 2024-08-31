from libs.core.types import *
from typing import Dict, List, Union
from libs.core.contexts import built_in_helpers, react_ctx, cli_ctx
from openai import Client
import jinja2
import json
from pydantic import create_model
import inspect, json
from inspect import Parameter
import instructor


def render_context(context: Context):
    env = jinja2.Environment()
    for helper_name, helper in built_in_helpers.items():
        env.globals[helper_name] = helper

    output = ""
    for sub_ctx in context.spec.contexts:
        output += render_context(sub_ctx) + "\n"

    template = env.from_string(context.spec.data)

    return output + template.render()


# def schema(f):
#     kw = {
#         n: (o.annotation, ... if o.default == Parameter.empty else o.default)
#         for n, o in inspect.signature(f).parameters.items()
#     }
#     s = create_model(f"Input for `{f.__name__}`", **kw).schema()
#     s["additionalProperties"] = False
#     return {
#         "type": "function",
#         "function": dict(
#             name=f.__name__, description=f.__doc__, strict=True, parameters=s
#         ),
#     }


class ExecCall(BaseModel):
    executable: Executable
    output: str


class ExecResult(BaseModel):
    calls: List[ExecCall]


class Observation(BaseModel):
    action: str
    observation: str


def exec_task(client: Client, task: Task, ask: bool = False):
    prompt = ""
    for ctx in task.spec.contexts:
        prompt += render_context(ctx) + "\n"

    prompt += "\nhere is the task instruction: \n"
    prompt += task.spec.instruction

    messages = [
        {"role": "user", "content": prompt},
    ]

    executables = []
    for ctx in task.spec.contexts:
        for executable in ctx.all_executables():
            executables.append(executable)

    instructor_client = instructor.from_openai(
        client, mode=instructor.Mode.PARALLEL_TOOLS
    )

    exec_calls = instructor_client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        response_model=Iterable[Union[tuple(executables)]],
    )

    exec_result = ExecResult(calls=[])
    for exec_call in exec_calls:
        output = exec_call()
        exec_result.calls.append(
            ExecCall(executable=exec_call, output=output.model_dump_json())
        )

    instructor_client = instructor.from_openai(client)

    messages.append(
        {
            "role": "user",
            "content": exec_result.model_dump_json(),
        }
    )

    resp = instructor_client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        response_model=task.spec.response_model,
    )
    # completion = client.beta.chat.completions.parse(
    #     model="gpt-4o-2024-08-06",
    #     messages=messages,
    #     tools=tools,
    #     response_format=task.spec.response_model,
    # )

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

    executables = []
    for ctx in task.spec.contexts:
        for executable in ctx.all_executables():
            executables.append(executable)

    messages = [
        {"role": "user", "content": prompt},
    ]

    instructor_client = instructor.from_openai(client)

    while True:
        resp = instructor_client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            response_model=ReactOutput,
        )

        output = resp.output
        if isinstance(output, ReactAnswer):
            return output.answer
        elif isinstance(output, ReactProcess):
            messages.append(
                {
                    "role": "user",
                    "content": output.model_dump_json(),
                }
            )
            if output.action is not None:
                task = Task(
                    metadata=task.metadata,
                    spec=TaskSpec(
                        instruction=output.action,
                        response_model=Observation,
                        contexts=task.spec.contexts,
                    ),
                )
                observation: Observation = exec_task(client, task)
                if observation is not None:
                    messages.append(
                        {
                            "role": "user",
                            "content": observation.model_dump_json(),
                        },
                    )
