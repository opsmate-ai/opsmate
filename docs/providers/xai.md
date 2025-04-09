We also support [xAI](https://x.ai/) as a provider.

## Configuration

xAI API key is required to use xAI models. You can set the API key using the `XAI_API_KEY` environment variable.

```bash
export XAI_API_KEY=<your-xai-api-key>
```

To find all the models supported by xAI, you can run:

```bash
opsmate list-models --provider xai
```

## Usage

You can specify the `-m` or `--model` option for the `run`, `solve`, and `chat` commands.

```bash
opsmate run -m grok-2-1212 "What is the OS?"
```

## See also

- [run](../CLI/run.md)
- [solve](../CLI/solve.md)
- [chat](../CLI/chat.md)
- [serve](../CLI/serve.md)
- [list-models](../CLI/list-models.md)
