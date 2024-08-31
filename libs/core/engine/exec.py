from libs.core.types import *
from typing import Union
from libs.core.contexts import react_ctx
from openai import Client
import instructor
import structlog
from .render import render_context

logger = structlog.get_logger()


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
        output = exec_call(ask=ask)
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
            logger.info(
                "react_process",
                question=output.question,
                thought=output.thought,
                action=output.action,
            )
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
                observation: Observation = exec_task(client, task, ask=ask)
                if observation is not None:
                    messages.append(
                        {
                            "role": "user",
                            "content": observation.model_dump_json(),
                        },
                    )
