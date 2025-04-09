By default Opsmate uses [OpenAI](https://openai.com/) as the default LLM provider, and `gpt-4o` as the default model.

To find all the models supported by OpenAI, you can run:

```bash
opsmate list-models --provider openai
```

At the moment we only support select models from OpenAI which produces reasonably good results.

## Configuration

OpenAI API key is required to use OpenAI models. You can set the API key using the `OPENAI_API_KEY` environment variable.

```bash
export OPENAI_API_KEY=<your-openai-api-key>
```

If your request goes through a proxy, you can set the `OPENAI_API_BASE` environment variable to the proxy URL.

```bash
export OPENAI_BASE_URL=<your-proxy-url>
```

Other configuration options such as `OPENAI_PROJECT_ID` and `OPENAI_ORG_ID` can be set using the environment variables. They will be picked up by the OpenAI SDK used by Opsmate.

```bash
export OPENAI_PROJECT_ID=<your-openai-project-id>
export OPENAI_ORG_ID=<your-openai-org-id>
```

## Usage

You can specify the `-m` or `--model` option for the `run`, `solve`, and `chat` commands.

```bash
# gpt-4o is the default model
opsmate run -m gpt-4o "What is the OS?"

# use gpt-4o-mini
opsmate run -m gpt-4o-mini "What is the OS?"
```

## See also

- [run](../CLI/run.md)
- [solve](../CLI/solve.md)
- [chat](../CLI/chat.md)
- [serve](../CLI/serve.md)
- [list-models](../CLI/list-models.md)
