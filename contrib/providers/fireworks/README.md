# opsmate-provider-fireworks

`opsmate-provider-fireworks` provides selected models from [Fireworks](https://fireworks.ai).

## Installation

```bash
opsmate install opsmate-provider-fireworks
```

After installation you can list all the models via

```bash
$ opsmate list-models
```

## Usage

You can specify the fireworks model in the `-m` flag.
```bash
export FIRWORKS_API_KEY="fw_..." # ideally save it in your shell profile
opsmate chat -m accounts/fireworks/models/deepseek-v3-0324
```

## Uninstall

```bash
opsmate uninstall -y opsmate-provider-fireworks
```
