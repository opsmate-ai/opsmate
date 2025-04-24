[Ollama](https://ollama.com/) is popular choice for running LLMs locally.

## Prerequisites

* You have already Ollama [installed on your machine](https://ollama.com/download).
* Ollama is up and running on your machine.

## Caution

Currently we have only experimented with Ollama on Apple Silicon with bunch of 7b - 12b parameter models. `gemma3:12b` so far is the only model that can produce barely acceptable results, and it's way behind in terms of quality and latency compared to frontier models.

That being said we encourage you to give it a try and [report any issues](https://github.com/opsmate-ai/opsmate/issues), especially for those who has 128GB+ vRAM to run bigger models.

## Usage

Assuming you have `gemma3:12b` model pulled via `ollama pull gemma3:12b`, you can run it with:
```bash
opsmate run --context cli-lite -m gemma3:12b "how many cores on the machine"
```

We strongly recommend you to use `cli-lite` context for running 7b - 12b parameter small models. You can find the prompt of `cli-lite` context in [cli_lite.py](https://github.com/opsmate-ai/opsmate/blob/main/opsmate/contexts/cli_lite.py).

To find all the ollama models you can run:

```bash
opsmate list-models --provider ollama
```

Behind the scene it fetches the list of models from `http://localhost:11434/v1/models`.

If you have a remote ollama server, you can point to the remote server with:

```bash
# by default it's http://localhost:11434/v1
export OLLAMA_BASE_URL=http://$YOUR_REMOTE_SERVER:11434/v1
```

## Further Exploration

The `cli-lite` context is far from optimal. To test your own prompt, you can create your own context in side `~/.opsmate/contexts` directory. The contexts in the directory will be loaded automatically by opsmate on startup.
