# GCE Runtime

This example demonstrates how to register a new runtime. In this case we are registering [GCE](https://cloud.google.com/compute) as the runtime for Opsmate.

## Installation

```bash
opsmate install -e .
```

After installation you can list the runtimes via

```bash
                                                   Runtimes
┏━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Name   ┃ Description                                                                                        ┃
┡━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ local  │ Local runtime allows model to execute tool calls within the same namespace as the opsmate process. │
├────────┼────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ docker │ Docker runtime allows model to execute tool calls within a docker container.                       │
├────────┼────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ ssh    │ SSH runtime allows model to execute tool calls on a remote server via SSH.                         │
├────────┼────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ gce    │ GCE runtime allows model to execute tool calls on a GCE instance using gcloud compute ssh.         │
└────────┴────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

You will notice that the GCE runtime is automatically added to the list of runtimes.

Here is an example of how to use the GCE runtime:

```bash
opsmate chat --shell-command-runtime gce \
  --runtime-gce-instance my-vm \
  --runtime-gce-zone europe-west1-c
```

This will start a chat with the GCE instance `my-vm` in the zone `europe-west1-c`.

## Uninstall

```bash
opsmate uninstall -y opsmate-runtime-gce
```
