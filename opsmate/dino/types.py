from pydantic import BaseModel, Field, computed_field, PrivateAttr, model_validator
from typing import (
    Any,
    List,
    Optional,
    Literal,
    Dict,
    Union,
    Type,
    TypeVar,
    Generic,
    Callable,
    Awaitable,
    TypeAlias,
    ClassVar,
)
from opentelemetry import trace
from opentelemetry.trace.status import Status, StatusCode
from opsmate.runtime import Runtime
from opsmate.libs.config import BaseSettings
from abc import ABC, abstractmethod
import structlog
import inspect
import traceback
import warnings

warnings.filterwarnings("ignore", message="fields may not start with an underscore")
logger = structlog.get_logger(__name__)
tracer = trace.get_tracer(__name__)


class TextContent(BaseModel):
    type: Literal["text"] = Field(description="The type of the content")
    text: str = Field(description="The text of the content")


class ImageURLContent(BaseModel):
    type: Literal["image_url"] = Field(
        description="The type of the content", default="image_url"
    )
    image_url: str | None = Field(
        description="The image url of the content", default=None
    )
    image_base64: str | None = Field(
        description="The base64 encoded image of the content", default=None
    )
    image_type: Literal["jpeg", "png", "webp", "gif"] = Field(
        description="The type of the image", default="jpeg"
    )
    detail: Literal["auto", "low", "high"] = Field(
        description="The detail of the image", default="auto"
    )

    @model_validator(mode="after")
    def validate_image_url_or_base64(self):
        if self.image_url is None and self.image_base64 is None:
            raise ValueError("Either image_url or image_base64 must be provided")

        return self


Content: TypeAlias = str | List[Union[TextContent, ImageURLContent]]


class Message(BaseModel):
    role: Literal["user", "assistant", "system"] = Field(
        description="The role of the message"
    )
    content: Content = Field(description="The content of the message")

    @classmethod
    def system(cls, content: Content):
        return cls(role="system", content=content)

    @classmethod
    def user(cls, content: Content):
        return cls(role="user", content=content)

    @classmethod
    def assistant(cls, content: Content):
        return cls(role="assistant", content=content)

    @classmethod
    def normalise(cls, messages: "ListOfMessageOrDict"):
        return [
            cls(**message) if isinstance(message, dict) else message
            for message in messages
        ]

    @classmethod
    def image_url_content(cls, image_url: str, detail: str = "auto"):
        return [ImageURLContent(image_url=image_url, detail=detail)]

    @classmethod
    def image_base64_content(
        cls, image_base64: str, image_type: str = "jpeg", detail: str = "auto"
    ):
        return [
            ImageURLContent(
                image_base64=image_base64, image_type=image_type, detail=detail
            )
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
    _tools: ClassVar[Dict[str, "ToolCall"]] = {}
    _tool_configs: ClassVar[Dict[str, "ToolCallConfig"]] = {}
    _tool_sources: ClassVar[Dict[str, str]] = {}

    _output: OutputType = PrivateAttr()

    async def run(self, context: dict[str, Any] = {}):
        """Run the tool call and return the output"""
        with tracer.start_as_current_span(
            name=f"{self.__class__.__name__}.run"
        ) as span:
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
                span.add_event(
                    "Tool call completed", attributes={"output": self.model_dump_json()}
                )
                span.set_status(StatusCode.OK)
            except Exception as e:
                logger.error(
                    "Tool execution failed",
                    error=str(e),
                    tool=self.__class__.__name__,
                    stack=traceback.format_exc(),
                )
                span.add_event("Tool call failed", attributes={"error": str(e)})
                span.set_status(StatusCode.ERROR, str(e))
                self.output = {
                    "error": str(e),
                    "message": "error executing tool",
                    "stack": traceback.format_exc(),
                }
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

    def display(self, context: dict[str, Any] = {}):
        if hasattr(self, "markdown"):
            return self.markdown(context=context)
        else:
            return self.prompt_display()

    def prompt_display(self):
        """
        prompt_display is the method that is called to display the tool call in the prompt.

        By default it returns the model_dump_json of the tool call.
        The reason we need this is because we want the output to be customisable.
        Especially when the tool call emits large amount of data, we don't want to
        over flow the context window.
        """
        return self.model_dump_json()

    async def confirmation_prompt(self, context: dict[str, Any] = {}):
        confirmation = context.get("confirmation", None)
        if confirmation is None:
            return True

        if inspect.iscoroutinefunction(confirmation):
            return await confirmation(self)
        else:
            return confirmation(self)

    def confirmation_fields(self) -> List[str]:
        """
        confirmation_fields is the method that is called to get the fields that are used to confirm the tool call.
        """
        return []


class ToolCallConfig(BaseSettings): ...


def register_tool(config: Type[ToolCallConfig] | None = None):
    def wrapper(cls: Type[ToolCall]):
        tool_name = cls.__name__
        ToolCall._tools[tool_name] = cls
        ToolCall._tool_sources[tool_name] = inspect.getfile(cls)
        if config:
            ToolCall._tool_configs[tool_name] = config
        return cls

    return wrapper


class PresentationMixin(ABC):
    @abstractmethod
    def markdown(self, context: dict[str, Any] = {}):
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
    observation: str = Field(description="The observation of the action", default="")

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
    description: str = Field(description="The description of the context", default="")

    # make system prompt coroutine as crafting the system prompt might involve network calls
    system_prompt: Optional[Callable[[dict[str, Runtime] | None], Awaitable[str]]] = (
        Field(description="The system prompt of the context", default=None)
    )
    contexts: List["Context"] = Field(
        description="The sub contexts to the context", default=[]
    )
    tools: List[Type[ToolCall]] = Field(
        description="The tools available in the context", default=[]
    )

    def resolve_tools(self):
        """resolve_tools aggregates all the tools from the context hierarchy"""
        tools = set(self.tools)
        for ctx in self.contexts:
            for tool in ctx.resolve_tools():
                if tool in tools:
                    logger.warning(
                        "Tool already defined in context",
                        tool=tool,
                        context=ctx.name,
                    )
                tools.add(tool)
        return tools

    async def resolve_contexts(self, runtimes: dict[str, Runtime] | None = None):
        """resolve_contexts aggregates all the contexts from the context hierarchy"""
        contexts = []
        if self.system_prompt:
            # Check if system_prompt expects a runtime parameter
            sig = inspect.signature(self.system_prompt)
            if "runtimes" in sig.parameters:
                # Function expects runtime parameter
                content = await self.system_prompt(runtimes=runtimes)
            else:
                # Function doesn't expect runtime parameter
                content = await self.system_prompt()
            contexts.append(Message.system(content))
        for ctx in self.contexts:
            contexts.extend(await ctx.resolve_contexts(runtimes=runtimes))
        return contexts
