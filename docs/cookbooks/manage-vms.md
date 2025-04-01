# Manage VMs via SSH

In this cookbook we will demonstrate how to manage VMs using Opsmate.

By default Opsmate runs shell commands in the same namespace as the opsmate process, but it also provides a `ssh` runtime that allows you to manage VMs using SSH. This is particularly useful when the virtual machine (VM) is:

- not accessible via the internet or running in an air-gapped network.
- cannot directly access the large language model (LLM) provider.
- a legacy system that cannot accommodate the runtime requirements of Opsmate (e.g. python 3.10+).


## Prerequisites

- A VM instance
- Opsmate CLI

## How to use the SSH runtime

The remote runtime is available to `run`, `solve` and `chat` commands.

Here is an example of how you can `chat` with a remote VM.

```bash
opsmate chat --runtime ssh \
    --runtime-ssh-host <vm-host> \
    --runtime-ssh-username <vm-username>
```

The following asciinema demo shows how to use the SSH runtime to "chat" with a remote VM.

```asciinema-player
{
    "file": "../assets/ssh-runtime.cast",
    "auto_play": true,
    "speed": 1.5
}
```
