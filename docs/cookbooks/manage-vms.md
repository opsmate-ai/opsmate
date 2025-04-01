# Manage VMs via SSH

In this cookbook we will demonstrate how to manage VMs using Opsmate.
Out of the box Opsmate comes with a `ssh` runtime that allows you to manage VMs using SSH.

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

```asciinema-player
{
    "file": "../assets/ssh-runtime.cast"
}
```
