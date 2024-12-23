from typing import List, Union, Callable, Coroutine, Any
from pydantic import BaseModel
from .dino import dino
from .types import Message, React, ReactAnswer, Observation, ToolCall
from functools import wraps
import inspect


async def _react_prompt(
    question: str, message_history: List[Message] = [], tools: List[BaseModel] = []
):
    """
    <assistant>
    You run in a loop of question, thought, action.
    At the end of the loop you output an answer.
    Use "Question" to describe the question you have been asked.
    Use "Thought" to describe your thought
    Use "Action" to describe the action you are going to take based on the thought.
    Use "Answer" as the final answer to the question.
    </assistant>

    <response format 1>
    During the thought phase you response with the following format:
    thought: ...
    action: ...
    </response_format 1>

    <response format 2>
    When you have an answer, you response with the following format:
    answer: ...
    </response_format 2>

    <important 1>
    When you know how to perform a task, provide the steps as an action rather than giving them as an answer.

    BAD EXAMPLE:
    <react>
    answer: to kill process with pid 1234, use `kill -TERM 1234`
    </react>

    GOOD EXAMPLE:

    <react>
    thought: I need to kill process using the kill command
    action: run `kill -TERM 1234`
    </react>
    </important 1 >

    <important 2>
    If you know the answer straight away, feel free to give the answer without going through the thought process.
    </important 2>
    """

    return [
        Message.user(
            f"""
Here is a list of tools you can use:
{"\n".join(f"<tool>{t.model_json_schema()}</tool>" for t in tools)}
""",
        ),
        Message.user(question),
        *message_history,
    ]


async def run_react(
    question: str,
    context: str = "",
    model: str = "gpt-4o",
    tools: List[ToolCall] = [],
    chat_history: List[Message] = [],
    max_iter: int = 10,
    react_prompt: Coroutine[Any, Any, List[Message]] = _react_prompt,
    **kwargs: Any,
):

    @dino(model, response_model=Observation, tools=tools, **kwargs)
    async def run_action(question: str, react: React):
        """
        You carry out action using the tools given
        based on the question, thought and action.
        """
        return [
            Message.system(context),
            Message.user(question),
            Message.assistant(react.model_dump_json()),
        ]

    react = dino(model, response_model=Union[React, ReactAnswer], **kwargs)(
        react_prompt
    )

    message_history = Message.normalise(chat_history)
    if context:
        message_history.append(Message.system(context))
    for _ in range(max_iter):
        react_result = await react(
            question, message_history=message_history, tools=tools
        )
        if isinstance(react_result, React):
            message_history.append(Message.assistant(react_result.model_dump_json()))
            yield react_result
            observation = await run_action(question, react_result)
            message_history.append(Message.assistant(observation.model_dump_json()))
            yield observation
        elif isinstance(react_result, ReactAnswer):
            yield react_result
            break


def react(
    model: str,
    tools: List[ToolCall] = [],
    context: str = "",
    max_iter: int = 10,
    iterable: bool = False,
    callback: Callable[[React | ReactAnswer | Observation], None] = None,
    react_kwargs: Any = {},
):
    """
    Decorator to run a function in a loop of question, thought, action.

    Example:
    @react(model="gpt-4o", tools=[knowledge_query], context="you are a domain knowledge expert")
    async def knowledge_agent(query: str):
        return f"answer the query: {query}"
    """

    def wrapper(fn):
        @wraps(fn)
        async def wrapper(*args, **kwargs):
            if inspect.iscoroutinefunction(fn):
                prompt = await fn(*args, **kwargs)
            else:
                prompt = fn(*args, **kwargs)

            if iterable:

                def gen():
                    return run_react(
                        prompt,
                        model=model,
                        context=context,
                        tools=tools,
                        max_iter=max_iter,
                        **react_kwargs,
                    )

                return gen()
            else:
                async for result in run_react(
                    prompt, context=context, tools=tools, max_iter=max_iter
                ):
                    if callback:
                        if inspect.iscoroutinefunction(callback):
                            await callback(result)
                        else:
                            callback(result)
                    if isinstance(result, ReactAnswer):
                        return result

        return wrapper

    return wrapper
