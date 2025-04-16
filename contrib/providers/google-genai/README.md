# opsmate-provider-google-genai

`opsmate-provider-google-genai` provides selected models from [Google GenAI](https://cloud.google.com/vertex-ai/generative-ai).

## Installation

```bash
opsmate install opsmate-provider-google-genai
```

After installation you can list all the models via

```bash
$ opsmate list-models
```

## Limitations

### Only Vertex AI models are supported
:warning: This provider currently does not support [Gemini API](https://ai.google.dev/gemini-api/docs/api-key), because the Gemini API [does not support `default` value](https://github.com/googleapis/python-genai/blob/edf6ee359fdce14d03e1e2c7b2dc50fa5b0fdee3/google/genai/_transformers.py#L653-L657) in the response schema.

As the result, currently only [vertex AI](https://cloud.google.com/vertex-ai) models are supported, meaning **you need to have a Google Cloud account in order to use this provider**.

### Limited region support for gemini-2.5-pro

By the time the provider is published, the `gemini-2.5-pro-preview-03-25` and `gemini-2.5-pro-exp-03-25` models are only available in the `us-central1` region. To use it you will need to set `GOOGLE_CLOUD_LOCATION` as below:

```bash
export GOOGLE_CLOUD_LOCATION=us-central1

# or
export GOOGLE_CLOUD_LOCATION=global
```

## Usage

```bash
export GOOGLE_CLOUD_PROJECT=<your-project-id>
export GOOGLE_CLOUD_LOCATION=<your-location>

opsmate chat -m gemini-2.0-flash-001
```

## Uninstall

```bash
opsmate uninstall -y opsmate-provider-google-genai
```
