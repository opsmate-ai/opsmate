from libs.core.types import *
from typing import Union
from libs.core.contexts import react_ctx
from openai import Client
import instructor
import structlog
from .render import render_context
import yaml

logger = structlog.get_logger()


def _exec_executables(
    client: Client, task: Task, ask: bool = False, model: str = "gpt-4o"
):
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
        model=model,
        messages=messages,
        response_model=Iterable[Union[tuple(executables)]],
    )

    exec_result = ExecResult(calls=[])
    try:
        for exec_call in exec_calls:
            output = exec_call(ask=ask)
        exec_result.calls.append(
            ExecCall(executable=exec_call, output=output.model_dump_json())
        )
    except Exception as e:
        logger.error(f"Error executing {exec_calls}: {e}")

    return exec_result, messages


def exec_task(client: Client, task: Task, ask: bool = False, model: str = "gpt-4o"):
    exec_result, messages = _exec_executables(client, task, ask, model)

    instructor_client = instructor.from_openai(client)

    messages.append(
        {
            "role": "user",
            "content": exec_result.model_dump_json(),
        }
    )

    resp = instructor_client.chat.completions.create(
        model=model,
        messages=messages,
        response_model=task.spec.response_model,
    )

    return resp


def exec_react_task(
    client: Client,
    task: Task,
    ask: bool = False,
    historic_context: List[ReactProcess | ReactAnswer] = [],
    model: str = "gpt-4o",
):
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

    messages = []
    messages.extend(
        {"role": "system", "content": yaml.dump(ctx.model_dump())}
        for ctx in historic_context
    )

    messages.append({"role": "user", "content": prompt})

    instructor_client = instructor.from_openai(client)

    while True:
        resp = instructor_client.chat.completions.create(
            model=model,
            messages=messages,
            response_model=ReactOutput,
        )

        output = resp.output
        if isinstance(output, ReactAnswer):
            historic_context.append(output)
            return output.answer, historic_context
        elif isinstance(output, ReactProcess):
            historic_context.append(output)
            logger.info(
                "react_process",
                question=output.question,
                thought=output.thought,
                action=output.action,
            )
            messages.append(
                {
                    "role": "user",
                    "content": yaml.dump(output.model_dump()),
                }
            )
            if output.action is not None:
                action_task = Task(
                    metadata=Metadata(
                        name="action",
                        apiVersion="v1",
                    ),
                    spec=TaskSpec(
                        instruction=output.action,
                        response_model=Observation,
                        contexts=task.spec.contexts,
                    ),
                )
                exec_result, _ = _exec_executables(
                    client, action_task, ask=ask, model=model
                )

                observation = Observation(
                    action=output.action,
                    observation=yaml.dump(exec_result.model_dump()),
                )
                if observation is not None:
                    messages.append(
                        {
                            "role": "user",
                            "content": yaml.dump(observation.model_dump()),
                        },
                    )
