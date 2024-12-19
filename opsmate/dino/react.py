from typing import List, Union
from pydantic import BaseModel
from .dino import dino
from .types import Message, React, ReactAnswer, Observation


async def _react_prompt(
    question: str, context: List[Message] = [], tools: List[BaseModel] = []
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
        Message(
            role="user",
            content=f"""
Here is a list of tools you can use:
{"\n".join(f"<tool>{t.model_json_schema()}</tool>" for t in tools)}
""",
        ),
        Message(role="user", content=question),
        *context,
    ]


def _react(model: str):
    return dino(model, response_model=Union[React, ReactAnswer])(_react_prompt)


async def run_react(
    question: str,
    pretext: str = "",
    model: str = "gpt-4o",
    tools: List[BaseModel] = [],
    max_iter: int = 10,
):

    @dino(model, response_model=Observation, tools=tools)
    async def run_action(react: React):
        return [
            Message(role="system", content=pretext),
            Message(role="assistant", content=react.model_dump_json()),
        ]

    react = _react(model)

    context = []
    if pretext:
        context.append(Message(role="system", content=pretext))
    for _ in range(max_iter):
        react_result = await react(question, context=context, tools=tools)
        if isinstance(react_result, React):
            context.append(
                Message(role="assistant", content=react_result.model_dump_json())
            )
            yield react_result
            observation = await run_action(react_result)
            context.append(
                Message(role="assistant", content=observation.model_dump_json())
            )
            yield observation
        elif isinstance(react_result, ReactAnswer):
            yield react_result
            break
