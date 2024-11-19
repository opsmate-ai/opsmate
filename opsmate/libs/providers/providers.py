import instructor
from instructor import Mode
from instructor.client import T, ChatCompletionMessageParam
from typing import List, Any, Dict, Literal, get_args
from openai import OpenAI
from anthropic import Anthropic
from anthropic.types import Model as AnthropicModel
import os

Provider = Literal["openai", "anthropic"]
ClientBag = Dict[Provider, OpenAI | Anthropic]


class Client:
    @classmethod
    def clients_from_env(cls):
        clients = {}
        if os.getenv("ANTHROPIC_API_KEY"):
            clients["anthropic"] = Anthropic()
        if os.getenv("OPENAI_API_KEY"):
            clients["openai"] = OpenAI()
        return clients

    def __init__(
        self,
        clients: ClientBag,
        provider: Provider,
        mode: Mode | None = None,
    ):
        self.messages = []
        self.system_prompt = ""
        self.provider = provider

        if provider == "openai":
            if mode is None:
                mode = Mode.TOOLS
            self.client = clients[provider]
            self.instructor_client = instructor.from_openai(self.client, mode=mode)
        elif provider == "anthropic":
            if mode is None:
                mode = Mode.ANTHROPIC_TOOLS
            self.client = clients[provider]
            self.instructor_client = instructor.from_anthropic(self.client, mode=mode)

    def chat_completion(
        self,
        model: str,
        response_model: type[T],
        max_retries: int = 3,
        validation_context: dict[str, Any] | None = None,
        context: dict[str, Any] | None = None,  # {{ edit_1 }}
        strict: bool = True,
        max_tokens: int = 4096,
    ):
        return self.instructor_client.chat.completions.create(
            model=model,
            response_model=response_model,
            messages=self.messages,
            max_retries=max_retries,
            validation_context=validation_context,
            context=context,
            max_tokens=max_tokens,
            strict=strict,
        )

    def append_messages(self, messages: List[ChatCompletionMessageParam]):
        for message in messages:
            self.messages.append(message)

    def assistant_content(self, content: str):
        self.messages.append({"role": "assistant", "content": content.strip()})

    def user_content(self, content: str):
        self.messages.append({"role": "user", "content": content.strip()})

    def system_content(self, content: str):
        if self.provider == "openai":
            self.messages.append({"role": "system", "content": content.strip()})
        elif self.provider == "anthropic":
            self.system_prompt += content.strip()

    def models(self):
        # if "openai" in self.clients:
        models = []
        if self.provider == "openai":
            model_names = [
                model.id
                for model in self.client.models.list().data
                if model.id.startswith("gpt")
            ]
            models.extend(model_names)

        if self.provider == "anthropic":
            for arg in get_args(AnthropicModel):
                if hasattr(arg, "__origin__") and arg.__origin__ is Literal:
                    models.extend(get_args(arg))

        return models
