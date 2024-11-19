import instructor
from instructor import Mode
from instructor.client import T, ChatCompletionMessageParam
from typing import List, Any, Dict, Literal, get_args
from openai import OpenAI
from anthropic import Anthropic
from anthropic.types import Model as AnthropicModel
import os


class Client:
    @classmethod
    def clients_from_env(cls):
        clients = {}
        if os.getenv("ANTHROPIC_API_KEY"):
            clients["anthropic"] = Anthropic()
        if os.getenv("OPENAI_API_KEY"):
            clients["openai"] = OpenAI()
        return clients

    @classmethod
    def from_env(cls):
        return cls(cls.clients_from_env())

    def __init__(self, clients: Dict[str, OpenAI | Anthropic]):
        self.clients = clients
        self.messages = []
        self.system_prompt = ""

    def _instructor_client(
        self,
        provider: str,
        mode: Mode | None = None,
    ) -> instructor.Instructor:
        if provider == "anthropic":
            if mode is None:
                mode = Mode.ANTHROPIC_TOOLS
            return instructor.from_anthropic(self.clients[provider], mode=mode)
        elif provider == "openai":
            if mode is None:
                mode = Mode.TOOLS
            return instructor.from_openai(self.clients[provider], mode=mode)
        else:
            raise ValueError(f"Invalid provider: {provider}")

    def chat_completion(
        self,
        provider: str,
        model: str,
        response_model: type[T],
        messages: List[ChatCompletionMessageParam],
        max_retries: int = 3,
        validation_context: dict[str, Any] | None = None,
        context: dict[str, Any] | None = None,  # {{ edit_1 }}
        strict: bool = True,
        max_tokens: int = 4096,
    ):
        instructor_client = self._instructor_client(provider)
        return instructor_client.chat.completions.create(
            model=model,
            response_model=response_model,
            messages=messages,
            max_retries=max_retries,
            validation_context=validation_context,
            context=context,
            max_tokens=max_tokens,
            strict=strict,
        )

    def assistant_content(self, content: str):
        self.messages.append({"role": "assistant", "content": content})

    def user_content(self, content: str):
        self.messages.append({"role": "user", "content": content})

    def system_content(self, content: str):
        if isinstance(self.client, OpenAI):
            self.messages.append({"role": "system", "content": content})
        elif isinstance(self.client, Anthropic):
            self.system_prompt += content

    def models(self):
        models = []
        if "openai" in self.clients:
            model_names = [
                model.id
                for model in self.clients["openai"].models.list().data
                if model.id.startswith("gpt")
            ]
            models.extend(model_names)

        if "anthropic" in self.clients:
            for arg in get_args(AnthropicModel):
                if hasattr(arg, "__origin__") and arg.__origin__ is Literal:
                    models.extend(get_args(arg))
        return models
