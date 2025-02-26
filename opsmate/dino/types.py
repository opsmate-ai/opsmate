from pydantic import BaseModel, Field, computed_field, PrivateAttr
from typing import Any, List, Optional, Literal, Dict, Union, Type, TypeVar, Generic
import structlog
from abc import ABC, abstractmethod
import inspect
import traceback
import warnings

warnings.filterwarnings("ignore", message="fields may not start with an underscore")
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


class React(BaseModel):
    thoughts: str = Field(description="Your thought about the question")
    action: str = Field(description="Action to take based on your thoughts")


class ReactAnswer(BaseModel):
    answer: str = Field(description="Your final answer to the question")


# Define a type variable
OutputType = TypeVar("OutputType")


class ToolCall(BaseModel, Generic[OutputType]):
    _output: OutputType = PrivateAttr()

    async def run(self, context: dict[str, Any] = {}):
        """Run the tool call and return the output"""
        try:
            if inspect.iscoroutinefunction(self.__call__):
                if self.call_has_context():
                    self.output = await self(context=context)
                else:
                    self.output = await self()
            else:
                if self.call_has_context():
                    self.output = self(context=context)
                else:
                    self.output = self()
        except Exception as e:
            logger.error(
                "Tool execution failed",
                error=str(e),
                tool=self.__class__.__name__,
                stack=traceback.format_exc(),
            )
            self.output = f"Error executing tool {self.__class__.__name__}: {str(e)}"
        return self.output

    @computed_field
    @property
    def output(self) -> OutputType:
        if hasattr(self, "_output"):
            return self._output
        else:
            return None

    @output.setter
    def output(self, value: OutputType):
        self._output = value

    def call_has_context(self):
        if not hasattr(self, "__call__"):
            return False
        sig = inspect.signature(self.__call__)
        return "context" in sig.parameters


class PresentationMixin(ABC):
    @abstractmethod
    def markdown(self):
        pass


class ResponseWithToolOutputs(BaseModel, Generic[OutputType]):
    _tool_outputs: List[OutputType] = PrivateAttr(default=[])

    @computed_field
    def tool_outputs(self) -> List[OutputType]:
        return self._tool_outputs

    @tool_outputs.setter
    def tool_outputs(self, value: List[OutputType]):
        self._tool_outputs = value


class Observation(ResponseWithToolOutputs[ToolCall]):
    observation: str = Field(description="The observation of the action")

    @computed_field
    @property
    def tool_outputs(self) -> List[ToolCall]:
        return self._tool_outputs

    @tool_outputs.setter
    def tool_outputs(self, value: List[ToolCall]):
        self._tool_outputs = value


class Context(BaseModel):
    """
    Context represents a collection of tools and contexts.
    It is used by the `react` decorator to build the context for the AI assistant.
    """

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
