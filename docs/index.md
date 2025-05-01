# Opsmate, The AI SRE teammate to free you from the toils of production engineering.

Opsmate is an LLM-powered SRE copilot for understanding and solving production problems. By encoding expert troubleshooting patterns and operational knowledge, Opsmate lets users describe problem statements and intentions in natural language, eliminating the need to memorise complex command line or domain-specific tool syntax.

Opsmate can not only perform problem solving autonomously, but also allow human operators to provide feedback and take over the control when needed. It accelerates incident response, reduces mean time to repair (MTTR), and empowers teams to focus on solving problems rather than wrestling with tooling.

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
    docker pull ghcr.io/opsmate-ai/opsmate:latest # or the specific version if you prefer not living on the edge
    alias opsmate="docker run -it --rm --env OPENAI_API_KEY=$OPENAI_API_KEY -v $HOME/.opsmate:/root/.opsmate ghcr.io/opsmate-ai/opsmate:latest"
    ```

=== "Source"
    ```bash
    git clone git@github.com:opsmate-ai/opsmate.git
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

## Quick Start

Run `opsmate run "what's the distro of the os"` to get the OS distribution of the host

Run `opsmate solve "resolve the high cpu usage on the server" --review` to solve the problem step by step and review the solution with human in the loop.

Run `opsmate chat --review` to chat with Opsmate.

Run `opsmate serve` to launch a notebook interface for Opsmate.

## Documentation

- [CLI Reference](./CLI/index.md) for simple command usage.
- [LLM Providers](./providers/index.md) for LLM provider configuration.
- [Tools](./tools/index.md) for tool usage.
- [Integrations](./configurations/add-new-llm-providers.md) and [Cookbooks](./cookbooks/index.md) for advanced usages.
- [Production](production.md) for how to production-grade Opsmate deployment behind local workstation usage.
