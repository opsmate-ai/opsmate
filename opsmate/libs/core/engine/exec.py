from opsmate.libs.core.types import *
from typing import Union, Callable
from opsmate.libs.core.contexts import react_ctx
from opsmate.libs.core.trace import traceit
from opentelemetry.trace import Span
from openai import Client
import instructor
import structlog
from .render import render_context
import yaml
from queue import Queue

logger = structlog.get_logger()


@traceit(exclude=["client", "task", "stream_output", "historic_context"])
def _exec_executables(
    client: Client,
    task: Task,
    ask: bool = False,
    model: str = "gpt-4o",
    max_retries: int = 3,
    stream: bool = False,
    stream_output: Queue = None,
    historic_context: List[ReactProcess | ReactAnswer | Observation] = [],
    span: Span = None,
):

    prompt = ""
    for ctx in task.spec.contexts:
        prompt += render_context(ctx) + "\n"

    messages = [
        {"role": "user", "content": prompt},
    ]

    messages.extend(
        {"role": "user", "content": yaml.dump(ctx.model_dump())}
        for ctx in historic_context
    )

    messages.append({"role": "user", "content": task.spec.instruction})

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
            if not stream:
                output = exec_call(ask=ask)
                exec_result.calls.append(
                    ExecCall(command=exec_call.command, output=output)
                )
            else:
                output = exec_call.stream(ask=ask)
                stream_output.put(exec_call)
                for out in output:
                    stream_output.put(out)
                    if out.exit_code != -1:
                        exec_result.calls.append(
                            ExecCall(command=exec_call.command, output=out)
                        )

    except Exception as e:
        logger.error(f"Error executing {exec_calls}: {e}")

    return exec_result, messages


@traceit(exclude=["client", "task"])
def exec_task(
    client: Client,
    task: Task,
    ask: bool = False,
    model: str = "gpt-4o",
    stream: bool = False,
    stream_output: Queue = None,
    span: Span = None,
):
    span.set_attribute("instruction", task.spec.instruction)

    exec_result, messages = _exec_executables(
        client, task, ask, model, stream=stream, stream_output=stream_output
    )

    instructor_client = instructor.from_openai(client)

    messages.append(
        {
            "role": "user",
            "content": yaml.dump(exec_result.model_dump()),
        }
    )

    resp = instructor_client.chat.completions.create(
        model=model,
        messages=messages,
        response_model=task.spec.response_model,
    )

    return resp


@traceit(exclude=["client", "task", "historic_context", "stream_output"])
def exec_react_task(
    client: Client,
    task: Task,
    ask: bool = False,
    historic_context: List[ReactProcess | Observation | ReactAnswer] = [],
    max_depth: int = 10,
    model: str = "gpt-4o",
    stream: bool = False,
    stream_output: Queue = None,
    span: Span = None,
):
    if task.spec.response_model != ReactOutput:
        raise ValueError("Task response model must be ReactOutput")

    if react_ctx not in task.spec.contexts:
        raise ValueError("React context is required for react task")

    if max_depth <= 0:
        raise ValueError("Max depth must be greater than 0")

    prompt = ""
    for ctx in task.spec.contexts:
        prompt += render_context(ctx) + "\n"

    messages = []
    messages.extend(
        {"role": "user", "content": yaml.dump(ctx.model_dump())}
        for ctx in historic_context
    )

    messages.append({"role": "user", "content": prompt})
    messages.append({"role": "user", "content": "question: " + task.spec.instruction})

    instructor_client = instructor.from_openai(client)

    answered = False
    for _ in range(max_depth):
        resp = instructor_client.chat.completions.create(
            model=model,
            messages=messages,
            response_model=ReactOutput,
        )

        output = resp.output
        if isinstance(output, ReactAnswer):
            historic_context.append(output)
            yield output
            answered = True
            break
        elif isinstance(output, ReactProcess):
            historic_context.append(output)
            yield output

            messages.append(
                {
                    "role": "user",
                    "content": yaml.dump(output.model_dump()),
                }
            )
            if output.action is not None and len(task.spec.contexts) > 1:
                ctx = task.spec.contexts.copy()
                ctx.remove(react_ctx)

                inst = {
                    "thought": output.thought,
                    "action": output.action,
                }
                action_task = Task(
                    metadata=Metadata(
                        name="action",
                    ),
                    spec=TaskSpec(
                        instruction=yaml.dump(inst),
                        response_model=Observation,
                        contexts=ctx,
                    ),
                )

                exec_result, _ = _exec_executables(
                    client,
                    action_task,
                    ask=ask,
                    model=model,
                    stream=stream,
                    stream_output=stream_output,
                    historic_context=historic_context,
                )

                observation = Observation(
                    action=output.action,
                    observation=yaml.dump(exec_result.model_dump()),
                )

                yield exec_result

                historic_context.append(observation)
                if observation is not None:
                    messages.append(
                        {
                            "role": "user",
                            "content": yaml.dump(observation.model_dump()),
                        },
                    )

    if not answered:
        logger.warning("No answer found")
