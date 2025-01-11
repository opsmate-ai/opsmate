# Opsmate, The AI SRE teammate to free you from the toils of production engineering.

_Modern infrastructure and production environments are complex, Opsmate is a SRE teammate that is available 24/7 to help you handle the production operations._

---

Opsmate makes it easy to manage production environments. It stands out from other current SRE tools because its human-in-the-loop approach - It can not only run autonomously but also allow the human operator to provide feedback and take over the control when needed.

## Getting Started

You can start using Opsmate by running it locally on your workstation. There are several ways to install Opsmate on your workstation:

=== "Source"
    ```bash
    git clone git@github.com:jingkaihe/opsmate.git
    cd opsmate

    poetry install

    pipx install ./dist/opsmate-0.1.10a1-py3-none-any.whl
    ```

=== "Pip"
    ```bash
    # Coming soon
    ```

Note that the Opsmate is powered by large language models. At the moment it supports OpenAI and Anthropic (more to come). To use Opsmate, you need to set the `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` environment variable.

```bash
export OPENAI_API_KEY="sk-proj..."
export ANTHROPIC_API_KEY="sk-ant-api03-..."
```

Check out:

- [CLI](cli.md) for simple command usage.
- [Production](production.md) for production use cases.
