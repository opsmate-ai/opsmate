# Opsmate, The AI SRE teammate to free you from the toils of production engineering.

_Modern infrastructure and production environments are complex, Opsmate is a SRE teammate that is available 24/7 to help you handle the production operations._

---

Opsmate makes it easy to manage production environments. It stands out from other current SRE tools because its human-in-the-loop approach - It can not only run autonomously but also allow the human operator to provide feedback and take over the control when needed.

## Getting Started

You can start using Opsmate by running it locally on your workstation. There are several ways to install Opsmate on your workstation:



=== "pip"
    ```bash
    pip install -U opsmate
    ```

=== "pipx"
    ```bash
    pipx install opsmate
    # or
    pipx upgrade opsmate
    ```

=== "Source"
    ```bash
    git clone git@github.com:jingkaihe/opsmate.git
    cd opsmate

    poetry build

    pipx install ./dist/opsmate-*.whl
    ```

Note that the Opsmate is powered by large language models. At the moment it supports

* [OpenAI](https://platform.openai.com/api-keys)
* [Anthropic](https://console.anthropic.com/settings/keys)
* [xAI](https://x.ai/api)

To use Opsmate, you need to set any one of the `OPENAI_API_KEY`, `ANTHROPIC_API_KEY` or `XAI_API_KEY` environment variables.

```bash
export OPENAI_API_KEY="sk-proj..."
export ANTHROPIC_API_KEY="sk-ant-api03-..."
export XAI_API_KEY="xai-..."
```

Check out:

- [CLI](cli.md) for simple command usage.
- [Production](production.md) for production use cases.
