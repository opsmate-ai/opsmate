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
opsmate chat --shell-command-runtime ssh \
    --runtime-ssh-host <vm-host> \
    --runtime-ssh-username <vm-username>
```

The following asciinema demo shows how to use the SSH runtime to "chat" with a remote VM.

{{ asciinema("/assets/ssh-runtime.cast") }}

Here are some of the common configuration options for the SSH runtime:

```bash
  --runtime-ssh-connect-retries INTEGER
                                  Set connect_retries (env:
                                  RUNTIME_SSH_CONNECT_RETRIES)  [default: 3]
  --runtime-ssh-timeout INTEGER   Set timeout (env: RUNTIME_SSH_TIMEOUT)
                                  [default: 10]
  --runtime-ssh-shell TEXT        Set shell_cmd (env: RUNTIME_SSH_SHELL)
                                  [default: /bin/bash]
  --runtime-ssh-key-file TEXT     Set key_file (env: RUNTIME_SSH_KEY_FILE)
  --runtime-ssh-password TEXT     Set password (env: RUNTIME_SSH_PASSWORD)
  --runtime-ssh-username TEXT     Set username (env: RUNTIME_SSH_USERNAME)
                                  [default: ""]
  --runtime-ssh-port INTEGER      Set port (env: RUNTIME_SSH_PORT)  [default:
                                  22]
  --runtime-ssh-host TEXT         Set host (env: RUNTIME_SSH_HOST)  [default:
                                  ""]
```
