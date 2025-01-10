from pydantic import BaseModel, Field
from typing import Any, List, Optional, Literal, Dict, Union, Type
import structlog
from abc import ABC, abstractmethod
import inspect

logger = structlog.get_logger(__name__)


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


class ToolCall(BaseModel):
    async def run(self):
        """Run the tool call and return the output"""
        if inspect.iscoroutinefunction(self.__call__):
            self.output = await self()
        else:
            self.output = self()
        return self.output


class PresentationMixin(ABC):
    @abstractmethod
    def markdown(self):
        pass


class Observation(BaseModel):
    tool_outputs: List[ToolCall] = Field(
        description="The output of the tools calling - as the AI assistant DO NOT populate this field",
        default=[],
    )
    observation: str = Field(description="The observation of the action")


class Context(BaseModel):
    name: str = Field(description="The name of the context")
    content: Optional[str] = Field(
        description="The description of the context", default=None
    )
    contexts: List["Context"] = Field(
        description="The sub contexts to the context", default=[]
    )
    tools: List[Type[ToolCall]] = Field(
        description="The tools available in the context", default=[]
    )

    def all_tools(self):
        tools = set(self.tools)
        for ctx in self.contexts:
            for tool in ctx.all_tools():
                if tool in tools:
                    logger.warning(
                        "Tool already defined in context",
                        tool=tool,
                        context=ctx.name,
                    )
                tools.add(tool)
        return tools

    def all_contexts(self):
        contexts = []
        if self.content:
            contexts.append(Message.system(self.content))
        for ctx in self.contexts:
            contexts.extend(ctx.all_contexts())
        return contexts
