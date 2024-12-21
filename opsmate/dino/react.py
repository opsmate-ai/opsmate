from typing import List, Union
from pydantic import BaseModel
from .dino import dino
from .types import Message, React, ReactAnswer, Observation


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


def _react(model: str):
    return dino(model, response_model=Union[React, ReactAnswer])(_react_prompt)


async def run_react(
    question: str,
    pretext: str = "",
    model: str = "gpt-4o",
    tools: List[BaseModel] = [],
    chat_history: List[Message] = [],
    max_iter: int = 10,
):

    @dino(model, response_model=Observation, tools=tools)
    async def run_action(question: str, react: React):
        """
        You carry out action using the tools given
        based on the question, thought and action.
        """
        return [
            Message.system(pretext),
            Message.user(question),
            Message.assistant(react.model_dump_json()),
        ]

    react = _react(model)

    message_history = Message.normalise(chat_history)
    if pretext:
        message_history.append(Message.system(pretext))
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
