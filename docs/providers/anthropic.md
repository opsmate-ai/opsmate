[Anthropic](https://www.anthropic.com/) is a large language model provider that, based on the vibe and evaluation metrics by far provides the best results.

## Configuration

Anthropic API key is required to use Anthropic models. You can set the API key using the `ANTHROPIC_API_KEY` environment variable.

```bash
export ANTHROPIC_API_KEY=<your-anthropic-api-key>
```

Like OpenAI we only support select models from Anthropic which produces reasonably good results.

To find all the models supported by Anthropic, you can run:

```bash
opsmate list-models --provider anthropic
```

## Usage

You can specify the `-m` or `--model` option for the `run`, `solve`, and `chat` commands.

```bash
opsmate run -m claude-3-5-sonnet-20241022 "What is the OS?"

# use claude-3-opus-20240229
opsmate run -m claude-3-7-sonnet-20250219 "What is the OS?"
```

## See also

- [run](../CLI/run.md)
- [solve](../CLI/solve.md)
- [chat](../CLI/chat.md)
- [serve](../CLI/serve.md)
- [list-models](../CLI/list-models.md)
