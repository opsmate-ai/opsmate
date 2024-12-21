from pydantic import BaseModel, Field
from typing import Any, List, Optional, Literal, Dict, Union


class Message(BaseModel):
    role: Literal["user", "assistant", "system"] = Field(
        description="The role of the message"
    )
    content: str = Field(description="The content of the message")

    @classmethod
    def system(cls, content: str):
        return cls(role="system", content=content)

    @classmethod
    def user(cls, content: str):
        return cls(role="user", content=content)

    @classmethod
    def assistant(cls, content: str):
        return cls(role="assistant", content=content)

    @classmethod
    def normalise(cls, messages: "ListOfMessageOrDict"):
        return [
            cls(**message) if isinstance(message, dict) else message
            for message in messages
        ]


MessageOrDict = Union[Dict, Message]
ListOfMessageOrDict = List[MessageOrDict]


class Result(BaseModel):
    result: Any = Field(description="The result of a dino run")
    tool_output: List[str | BaseModel] = Field(
        description="The output of the tools used in the dino run"
    )


class React(BaseModel):
    thoughts: str = Field(description="Your thought about the question")
    action: str = Field(description="Action to take based on your thoughts")


class ReactAnswer(BaseModel):
    answer: str = Field(description="Your final answer to the question")


class ToolOutput(BaseModel): ...


class Observation(BaseModel):
    tool_outputs: List[ToolOutput] = Field(
        description="The output of the tools calling - as the AI assistant DO NOT populate this field",
        default=[],
    )
    observation: str = Field(description="The observation of the action")
