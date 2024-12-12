from opsmate.libs.core.types import *
from typing import Union, Callable
from opsmate.libs.core.contexts import react_ctx
from opsmate.libs.core.trace import traceit
from opentelemetry.trace import Span
from opsmate.libs.providers import Client as ProviderClient, ClientBag
import instructor
from instructor import Mode
import structlog
from .render import render_context, render_tools
import yaml
from queue import Queue

logger = structlog.get_logger()


@traceit(exclude=["clients", "task", "stream_output", "historic_context"])
def _exec_executables(
    clients: ClientBag,
    task: Task,
    ask: bool = False,
    provider: str = "openai",
    model: str = "gpt-4o",
    max_retries: int = 3,
    stream: bool = False,
    stream_output: Queue = None,
    historic_context: List[ReactProcess | ReactAnswer | Observation] = [],
    span: Span = None,
):
    provider_client = ProviderClient(clients, provider, mode=Mode.PARALLEL_TOOLS)

    prompt = ""
    for ctx in task.spec.contexts:
        prompt += render_context(ctx) + "\n"

    provider_client.system_content(prompt)

    for ctx in historic_context:
        provider_client.assistant_content(yaml.dump(ctx.model_dump()))

    provider_client.system_content(render_tools(task))

    provider_client.user_content(yaml.dump({"question": task.spec.instruction}))

    executables = list(task.all_executables)

    for retry_count in range(max_retries):
        try:
            exec_calls = provider_client.chat_completion(
                model=model,
                max_retries=max_retries,
                response_model=Iterable[Union[tuple(executables)]],
            )

            exec_results = ExecResults(results=[])

            for exec_call in exec_calls:
                if not stream or not exec_call.streamable:
                    output = exec_call(ask=ask)
                    logger.info(f"output: {output}")
                    exec_results.results.append(output)
                else:
                    outputs = exec_call.stream(ask=ask)
                    stream_output.put(exec_call)
                    for output in outputs:
                        stream_output.put(output)
                        if output.exit_code != -1:
                            exec_results.results.append(output)

            span.set_attribute("exec_results.len", len(exec_results.results))
            break  # Success - exit retry loop

        except Exception as e:
            logger.error(f"Attempt {retry_count + 1} failed: {e}", exc_info=True)
            if retry_count == max_retries - 1:  # Last attempt
                logger.error(f"All {max_retries} attempts failed")
                raise  # Re-raise the last exception

    return exec_results, provider_client.messages


@traceit(exclude=["client", "task"])
def exec_task(
    clients: ClientBag,
    task: Task,
    ask: bool = False,
    provider: str = "openai",
    model: str = "gpt-4o",
    stream: bool = False,
    stream_output: Queue = None,
    span: Span = None,
):
    span.set_attribute("instruction", task.spec.instruction)

    exec_result, _ = _exec_executables(
        clients=clients,
        task=task,
        ask=ask,
        provider=provider,
        model=model,
        stream=stream,
        stream_output=stream_output,
    )

    return exec_result


@traceit(exclude=["client", "task", "historic_context", "stream_output"])
def exec_react_task(
    clients: ClientBag,
    task: Task,
    ask: bool = False,
    historic_context: List[ReactProcess | Observation | ReactAnswer] = [],
    max_depth: int = 10,
    provider: str = "openai",
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

    provider_client = ProviderClient(clients, provider)
    for ctx in historic_context:
        provider_client.assistant_content(yaml.dump(ctx.model_dump()))

    prompt = ""
    for ctx in task.spec.contexts:
        prompt += render_context(ctx) + "\n"

    prompt += render_tools(task)

    provider_client.system_content(prompt)
    provider_client.user_content(yaml.dump({"question": task.spec.instruction}))

    answered = False
    for _ in range(max_depth):
        resp = provider_client.chat_completion(
            model=model,
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

            provider_client.assistant_content(yaml.dump(output.model_dump()))
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

                exec_results, _ = _exec_executables(
                    clients=clients,
                    task=action_task,
                    ask=ask,
                    provider=provider,
                    model=model,
                    stream=stream,
                    stream_output=stream_output,
                    historic_context=historic_context,
                )

                observation = Observation(
                    action=output.action,
                    observation=yaml.dump(exec_results.model_dump()),
                )

                yield exec_results

                historic_context.append(observation)
                if observation is not None:
                    provider_client.assistant_content(
                        yaml.dump(observation.model_dump())
                    )

    if not answered:
        logger.warning("No answer found")
