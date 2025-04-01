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
=== "uvx"
    ```bash
    uvx opsmate [OPTIONS] COMMAND [ARGS]...
    ```

=== "Docker"
    ```bash
    # Note this is less useful as you cannot access the host from the container
    # But still useful to interact with cloud API in an isolated containerised environment
    docker pull ghcr.io/jingkaihe/opsmate:latest # or the specific version if you prefer not living on the edge
    alias opsmate="docker run -it --rm --env OPENAI_API_KEY=$OPENAI_API_KEY -v $HOME/.opsmate:/root/.opsmate ghcr.io/jingkaihe/opsmate:latest"
    ```

=== "Source"
    ```bash
    git clone git@github.com:jingkaihe/opsmate.git
    cd opsmate

    uv build

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

- [CLI](./CLI/index.md) for simple command usage.
- [Production](production.md) for production use cases.
