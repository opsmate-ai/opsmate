[Fireworks AI](https://www.fireworks.ai/) is another LLM inference provider that supports a wide range of models. Notably it supports models such as deepseek and llama that comes with 400B+ parameters with affordable prices.

## Installation

Fireworks AI is not installed by default in Opsmate. You can install it using the following command:

```bash
opsmate install opsmate-provider-fireworks
```

## Configuration

Fireworks AI API key is required to use Fireworks AI models. You can set the API key using the `FIREWORKS_API_KEY` environment variable.

```bash
export FIREWORKS_API_KEY=<your-fireworks-api-key>

# You can also proxy the API calls to an alternative endpoint
export FIREWORKS_BASE_URL=<your-fireworks-base-url>
```

To find all the models supported by Fireworks AI, you can run:

```bash
opsmate list-models --provider fireworks
```

## Usage

You can specify the `-m` or `--model` option for the `run`, `solve`, and `chat` commands.

```bash
# deepseek-v3-0324 comes with 671B parameters
opsmate run -m accounts/fireworks/models/deepseek-v3-0324 "What is the OS?"
```

## See also

- [run](../CLI/run.md)
- [solve](../CLI/solve.md)
- [chat](../CLI/chat.md)
- [serve](../CLI/serve.md)
