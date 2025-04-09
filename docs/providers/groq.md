[Groq](https://groq.com/) provides fast inference with affordable prices. It supports a wide range of open-weight models.

## Installation

Groq is not installed by default in Opsmate. You can install it using the following command:

```bash
opsmate install opsmate-provider-groq
```

## Configuration

Groq API key is required to use Groq models. You can set the API key using the `GROQ_API_KEY` environment variable.

```bash
export GROQ_API_KEY=<your-groq-api-key>
```

To find all the models supported by Groq, you can run:

```bash
opsmate list-models --provider groq
```

## Usage

You can specify the `-m` or `--model` option for the `run`, `solve`, and `chat` commands.

```bash
opsmate run -m llama-3.3-70b-versatile "What is the OS?"
```

## See also

- [run](../CLI/run.md)
- [solve](../CLI/solve.md)
- [chat](../CLI/chat.md)
- [serve](../CLI/serve.md)
- [list-models](../CLI/list-models.md)
