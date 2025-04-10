# Opsmate


[![PyPI version](https://badge.fury.io/py/opsmate.svg)](https://badge.fury.io/py/opsmate)
[![Container Image](https://ghcr-badge.egpl.dev/jingkaihe/opsmate/latest_tag?trim=major&label=image&nbsp;tag)](https://github.com/jingkaihe/opsmate/pkgs/container/opsmate)
[![Link to documentation](https://img.shields.io/static/v1?label=%F0%9F%93%96&message=Documentation&color=blue)](https://docs.tryopsmate.ai/)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

Opsmate is an AI SRE teammate to free you from the toils of production engineering.

<img src="assets/demo.gif" width="700">

Modern infrastructure and production environments are complex. Opsmate is a 24/7 available SRE teammate that helps you manage production operations with a human-in-the-loop approach.

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Configuration](#configuration)
- [Quick Start](#quick-start)
- [Advanced Usage](#advanced-usage)
- [Use Cases](#use-cases)
- [Integrations](#integrations)
- [Documentation](#documentation)
- [Contributing](#contributing)
- [License](#license)

## Features

- 🤖 **Natural Language Interface**: Run commands using natural language without remembering complex syntax
- 🔍 **Advanced Reasoning**: Troubleshoot and solve production issues with AI-powered reasoning
- 🔄 **Multiple LLM Support**: Out of box works for OpenAI, Anthropic, xAI. [Easy to extend](./docs/integrations/add-new-llm-providers.md) to other LLMs.
- 🛠️ **Multiple Runtimes**: Supports various execution environments such as Local, [Docker](./docs/cookbooks/docker-runtime.md), [Kubernetes](./docs/cookbooks/k8s-runtime.md) and [remote VMs](./docs/cookbooks/manage-vms.md).
- 🔭 **Modern Observability Tooling**: Built-in support for [Prometheus](https://prometheus.io/) allows you to create time series dashboards with natural language, and more to come.
- 🧠 **Knowledge Management**: Ingest and use domain-specific knowledge
- 📈 **Web UI & API**: Access Opsmate through a web interface or API
- 🔌 **Plugin System**: Extend Opsmate with custom plugins

## Installation

Choose your preferred installation method:

The recommended way of installing opsmate is using `uv`:

```bash
# Using uvx
uv tool install -U opsmate
```

Other than that, you can also install opsmate using `pip`, `pipx` or `docker`.
```bash
# Using pip
pip install -U opsmate

# Using pipx
pipx install opsmate
# or
pipx upgrade opsmate

# Using Docker
docker pull ghcr.io/jingkaihe/opsmate:latest
alias opsmate="docker run -it --rm --env OPENAI_API_KEY=$OPENAI_API_KEY -v $HOME/.opsmate:/root/.opsmate ghcr.io/jingkaihe/opsmate:latest"

# From source
git clone git@github.com:jingkaihe/opsmate.git
cd opsmate
uv build
pipx install ./dist/opsmate-*.whl
```

## Configuration

Opsmate is powered by large language models. It currently supports:

* [OpenAI](https://platform.openai.com/api-keys)
* [Anthropic](https://console.anthropic.com/settings/keys)
* [xAI](https://x.ai/api)

Set up your API key in an environment variable:

```bash
export OPENAI_API_KEY="sk-proj..."
# or
export ANTHROPIC_API_KEY="sk-ant-api03-..."
# or
export XAI_API_KEY="xai-..."
```

## Quick Start

### Run commands with natural language

```bash
$ opsmate run "what's the gpu of the vm"
# Output: Command and result showing GPU information
```

### Solve complex production issues

```bash
$ opsmate solve "what's the k8s distro of the current context"
# Output: Thought process and analysis determining K8s distribution
```

### Interactive chat mode

```bash
$ opsmate chat
```

### Web UI and API

```bash
$ opsmate serve
# Web interface: http://localhost:8080
# API documentation: http://localhost:8080/api/docs
```

## Advanced Usage

Opsmate can be deployed in production environments using the `opsmate-operator` in a Kubernetes cluster, providing:

- Task scheduling via CRDs
- Dedicated HTTPS endpoints and web UI for tasks
- Multi-tenancy support
- Automatic resource management with TTL
- API server for environment management

Check our [production documentation](https://docs.tryopsmate.ai/production/) for details.

## Use Cases

Opsmate supports various use cases:

- Production issue troubleshooting and resolution
- Root cause analysis
- Performance analysis and improvement
- Observability and monitoring setup
- Capacity planning
- On-call engineer assistance
- Infrastructure as Code management
- Routine task automation (CI/CD, backups, updates)
- Knowledge management
- Workflow orchestration

## Integrations

For a comprehensive list of integrations, please refer to the [integrations](https://docs.tryopsmate.ai/integrations/add-new-llm-providers/) and [cookbooks](https://docs.tryopsmate.ai/cookbooks/) sections.

## Documentation

For comprehensive documentation, visit [here](https://docs.tryopsmate.ai).

## Contributing

Contributions are welcome! See our [development guide](docs/development.md) for details.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
