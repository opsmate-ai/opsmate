`opsmate list-runtimes` lists all the runtimes available.

## OPTIONS

```
Usage: opsmate list-runtimes [OPTIONS]

  List all the runtimes available.

Options:
  --help  Show this message and exit.
```

## USAGE

The command below will list all the runtimes available to Opsmate.

```bash
opsmate list-runtimes
                                                   Runtimes
┏━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Name   ┃ Description                                                                                        ┃
┡━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ local  │ Local runtime allows model to execute tool calls within the same namespace as the opsmate process. │
├────────┼────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ docker │ Docker runtime allows model to execute tool calls within a docker container.                       │
├────────┼────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ ssh    │ SSH runtime allows model to execute tool calls on a remote server via SSH.                         │
└────────┴────────────────────────────────────────────────────────────────────────────────────────────────────┘
```
