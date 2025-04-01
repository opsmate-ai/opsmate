Opsmate out-of-box supports OpenAI, Anthropic and xAI as the LLM providers. We plan to add more providers in the future. In the meantime you can also add your own LLM provider that are currently not supported by Opsmate.

In this article we will demonstrate how to add a new LLM provider by using [Groq](https://groq.com) as an example.

The full code for this example can be found [here](https://github.com/opsmate/opsmate/tree/main/examples/providers/groq).

## Prerequisites

- Python 3.12+
- Groq API key
- You already have Opsmate installed - If not, you can install it by following the [installation guide](../index.md#getting-started)
- Python virtual environment - It's not mandatory but highly recommended to use a virtual environment to install the dependencies for testing purposes.

## Steps

### Step 1: Create a new directory for the provider

```bash
mkdir -p groq
cd groq
touch provider_groq.py # This is the file that will contain the provider code
touch pyproject.toml # This is the file that will contain plugin metadata
```

### Step 2: Implement the provider code

```python
from opsmate.dino.provider import Provider, register_provider
from opsmate.dino.types import Message
from typing import Any, Awaitable, List
from instructor.client import T
from instructor import AsyncInstructor
from tenacity import AsyncRetrying
from functools import cache
from groq import AsyncGroq
import instructor
import os


@register_provider("groq")
class GroqProvider(Provider):
    DEFAULT_BASE_URL = "https://api.groq.com"

    # Here is the full list of models that support tool use https://console.groq.com/docs/tool-use
    models = [
        "qwen-2.5-32b",
        "deepseek-r1-distill-qwen-32b",
        "deepseek-r1-distill-llama-70b",
        "llama-3.3-70b-versatile",
        # commented out as it cannot reliably use tools
        # "llama-3.1-8b-instant",
        # "mixtral-8x7b-32768",
        # "gemma2-9b-it",
    ]

    @classmethod
    async def chat_completion(
        cls,
        response_model: type[T],
        messages: List[Message],
        max_retries: int | AsyncRetrying = 3,
        validation_context: dict[str, Any] | None = None,
        context: dict[str, Any] | None = None,
        strict: bool = True,
        client: AsyncInstructor | None = None,
        **kwargs: Any,
    ) -> Awaitable[T]:
        client = client or cls.default_client()
        kwargs.pop("client", None)

        messages = [{"role": m.role, "content": m.content} for m in messages]

        filtered_kwargs = cls._filter_kwargs(kwargs)
        return await client.chat.completions.create(
            response_model=response_model,
            messages=messages,
            max_retries=max_retries,
            validation_context=validation_context,
            context=context,
            strict=strict,
            **filtered_kwargs,
        )

    @classmethod
    @cache
    def _default_client(cls) -> AsyncInstructor:
        return instructor.from_groq(
            AsyncGroq(
                base_url=os.getenv("GROQ_BASE_URL", cls.DEFAULT_BASE_URL),
                api_key=os.getenv("GROQ_API_KEY"),
            ),
            mode=instructor.Mode.JSON,
        )
```

The minimum requirements for the new provider code includes:

- The `@register_provider` function that decorate the class that implements the `dino.provider.Provider`. Note that not only the provider class must implement the `dino.provider.Provider` interface and being decorated with `@register_provider` but also it needs to be a subclass of `Provider`.
- The `models` class variable that lists the models that the provider supports.
- The `chat_completion` method that implements the `Provider` interface.
- The `default_client` method that returns a `AsyncInstructor` client.

Note that the `chat_completion` method must be an async method, and the `default_client` must returns an `AsyncInstructor` client.

### Step 3: Implement plugin in `pyproject.toml`

```toml
[project]
name = "opsmate-provider-groq"
version = "0.1.0"
description = "Groq provider for opsmate"
dependencies = [
    "opsmate",
    "groq",
]

[project.entry-points."opsmate.dino.providers"]
groq = "provider_groq:GroqProvider"
```

Note that in the `pyproject.toml` file:

- We use `opsmate-provider-groq` as the name of the provider. It is not mandatory but `opsmate-provider-<provider-name>` is the convention we follow.
- We also use `groq` and `opsmate` as the dependencies.
- The `[project.entry-points."opsmate.dino.providers"]` section is used to register the provider. The name of the entry point group **MUST** be `opsmate.dino.providers`.
- We use `groq` as the name of the entry point, which points to the `provider_groq:GroqProvider` class.

If you are not familar with Python entry point based plugin system, you can refer to [this document](https://setuptools.pypa.io/en/latest/userguide/entry_point.html#entry-points-for-plugins).

### Step 4: Install the dependencies

```bash
opsmate install -e .
```

### Step 5: Test the provider

After installation you can list all the models via

```bash
$ opsmate list-models
                   Models
┏━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Provider  ┃ Model                         ┃
┡━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ openai    │ gpt-4o                        │
├───────────┼───────────────────────────────┤
│ openai    │ gpt-4o-mini                   │
├───────────┼───────────────────────────────┤
│ openai    │ o1-preview                    │
├───────────┼───────────────────────────────┤
│ anthropic │ claude-3-5-sonnet-20241022    │
├───────────┼───────────────────────────────┤
│ anthropic │ claude-3-7-sonnet-20250219    │
├───────────┼───────────────────────────────┤
│ xai       │ grok-2-1212                   │
├───────────┼───────────────────────────────┤
│ groq      │ qwen-2.5-32b                  │
├───────────┼───────────────────────────────┤
│ groq      │ deepseek-r1-distill-qwen-32b  │
├───────────┼───────────────────────────────┤
│ groq      │ deepseek-r1-distill-llama-70b │
├───────────┼───────────────────────────────┤
│ groq      │ llama-3.3-70b-versatile       │
└───────────┴───────────────────────────────┘
```

You will notice that the models from Groq are automatically added to the list of models.

You can use the `-m` flag to specify the model to use. For example:

```bash
export OPSMATE_LOGLEVEL=ERROR
$ opsmate run -n --tools HtmlToText -m llama-3.3-70b-versatile "find me top 10 news on the hacker news, titl
e only in bullet points"
The top 10 news on Hacker News are:
* The most unhinged video wall, made out of Chromebooks
* Show HN: Berlin Swapfest – Electronics flea market
* GLP-1 drugs – the biggest economic disruptor since the internet? (2024)
* Efabless – Shutdown Notice
* Video encoding requires using your eyes
* Making o1, o3, and Sonnet 3.7 hallucinate for everyone
* How to gain code execution on hundreds of millions of people and popular apps
* Show HN: I made a website where you can create your own "Life in Weeks" timeline
* Drone captures narwhals using their tusks to explore, forage and play
* Maestro – Next generation mobile UI automation
```

### Cleanup

```bash
opsmate uninstall -y opsmate-provider-groq
```
