By default Opsmate executes commands in the same environment as the `opsmate` process, however in some cases you might want to execute the code in a remote runtime. It can be the case of:

- You want to remote-ssh into a machine and perform troubleshooting and service maintenance.
- The target environment is rather legacy that doesn't support Python 3.10+, which is the minimum version required by Opsmate.
- You are not allowed to install software on the target remote runtime, thus there is no way to install Opsmate.
- The target runtime doesn't have internet access, thus it's not possible to access the large language models.

Out of box Opsmate supports the following runtimes:

- Local
- SSH
- Docker and Docker Compose

That being said nothing prevents you from integrating with a new runtime. In this article we will use Google Compute Engine as an example and create `opsmate-gce-runtime` plugin.

The full code for this example can be found [here](https://github.com/jingkaihe/opsmate/tree/main/examples/runtime/gce).

## Prerequisites

- You already have Opsmate installed - If not, you can install it by following the [installation guide](../index.md#getting-started)
- You have `gcloud` CLI installed
- You have set up the `gcloud` CLI and are authenticated to your Google Cloud account

## Steps

### Step 0: Create a GCE instance

```bash
export NETWORK=<your-network>
export SUBNET=<your-subnet>
export ZONE=europe-west1-c # Replace with your zone

# Create a firewall rule to allow SSH access
gcloud compute firewall-rules create allow-ssh \
  --network=$NETWORK \
  --direction=INGRESS \
  --priority=1000 \
  --source-ranges=0.0.0.0/0 \
  --action=ALLOW \
  --rules=tcp:22 \
  --target-tags=allow-ssh

gcloud compute instances create my-vm \
  --tags=allow-ssh \
  --zone=$ZONE \
  --network=$NETWORK \
  --subnet=$SUBNET \
  --no-address \
  --machine-type=n1-standard-1 \
  --image-project=ubuntu-os-cloud \
  --image-family=ubuntu-2404-lts-amd64
```

### Step 1: Create a new directory for the runtime

```bash
mkdir -p gce
cd gce
touch gce.py # This is the file that will contain the runtime code
touch pyproject.toml # This is the file that will contain runtime plugin metadata
```

### Step 2: Implement the runtime code

The runtime code can be found [here](https://github.com/jingkaihe/opsmate/blob/main/examples/runtime/gce/gce.py). In the code below we highlight the parts that are essential for the runtime integration, namely:

- The `GCERuntimeConfig` class that defines the configuration for the runtime.
- The `GCERuntime` class that implements the runtime.

The mandatory methods to be implemented for any runtimes are:

  - `connect` - Connect to the runtime.
  - `disconnect` - Disconnect from the runtime.
  - `run` in the case below it inherits from `LocalRuntime`.
  - `os_info` - Get OS information from the remote runtime.
  - `whoami` - Get current user information from the remote runtime.
  - `has_systemd` - Check if the remote runtime uses systemd.
  - `runtime_info` - Return information about the runtime.

For the `GCERuntime` it inherits from `LocalRuntime` and thus it can use the `co` function to execute commands.

```python
import os
import asyncio
from opsmate.runtime.runtime import (
    register_runtime,
    RuntimeConfig,
    RuntimeError,
    co,
)
from opsmate.runtime.local import LocalRuntime
from pydantic import Field, ConfigDict
from typing import List
import structlog


logger = structlog.get_logger(__name__)


class GCERuntimeConfig(RuntimeConfig):
    instance_name: str = Field(alias="RUNTIME_GCE_INSTANCE", default="")
    # ...


@register_runtime("gce", GCERuntimeConfig)
class GCERuntime(LocalRuntime):
    """GCE runtime allows model to execute tool calls on a GCE instance using gcloud compute ssh."""

    def __init__(self, config: GCERuntimeConfig):
        ...

    async def connect(self):
        """Connect to the GCE instance with retry logic."""
        ...

    async def disconnect(self):
        """Disconnect from the GCE instance and clean up resources."""
        ...

    async def os_info(self):
        """Get OS information from the remote GCE instance."""
        ...

    async def whoami(self):
        """Get current user information from the remote GCE instance."""
        ...

    async def has_systemd(self):
        """Check if the remote GCE instance uses systemd."""
        ...

    async def runtime_info(self):
        """Return information about the GCE runtime."""
        ...
```

### Step 3: Declare the runtime metadata in `pyproject.toml`

Opmsate has a `pip` based plugin system that allows you to load the runtime plugins as a python package. To do so you need to declare the runtime metadata in the `pyproject.toml`, as shown below:

```toml
[project]
name = "opsmate-runtime-gce"
version = "0.1.0"
description = "GCE runtime for opsmate"
dependencies = [
    "opsmate",
]

[project.entry-points."opsmate.runtime.runtimes"]
gce = "gce:GCERuntime"
```

Note that in the `pyproject.toml` file:

- We use `opsmate-runtime-gce` as the name of the runtime. It is not mandatory but `opsmate-runtime-<runtime-name>` is the convention we follow.
- We declare `opsmate` as the dependency.
- The `[project.entry-points."opsmate.runtime.runtimes"]` section is used to register the runtime. The name of the entry point group **MUST** be `opsmate.runtime.runtimes`.
- We use `gce` as the name of the entry point, which points to the `gce:GCERuntime` class.

### Step 4: Install the runtime plugin

```bash
opsmate install -e .
```

### Step 5: Validate the runtime has been installed

```bash
$ opsmate list-runtimes
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

We can also run `opsmate chat --help | grep -i gce` to validate that the runtime is available:

```bash
opsmate chat --help | grep -i gce
  --runtime-gce-extra-flags TEXT  Set extra_flags (env:
                                  RUNTIME_GCE_EXTRA_FLAGS)  [default: ""]
  --runtime-gce-gcloud-binary TEXT
                                  RUNTIME_GCE_GCLOUD_BINARY)  [default:
  --runtime-gce-connect-retries INTEGER
                                  RUNTIME_GCE_CONNECT_RETRIES)  [default: 3]
  --runtime-gce-timeout INTEGER   Set timeout (env: RUNTIME_GCE_TIMEOUT)
  --runtime-gce-shell TEXT        Set shell_cmd (env: RUNTIME_GCE_SHELL)
  --runtime-gce-iap-options TEXT  Set iap_tunnel_options (env:
                                  RUNTIME_GCE_IAP_OPTIONS)  [default: ""]
  --runtime-gce-use-iap BOOLEAN   Set use_iap (env: RUNTIME_GCE_USE_IAP)
  --runtime-gce-username TEXT     Set username (env: RUNTIME_GCE_USERNAME)
  --runtime-gce-project TEXT      Set project (env: RUNTIME_GCE_PROJECT)
  --runtime-gce-zone TEXT         Set zone (env: RUNTIME_GCE_ZONE)  [default:
  --runtime-gce-instance TEXT     Set instance_name (env:
                                  RUNTIME_GCE_INSTANCE)  [default: ""]
```

### Step 6: Test the runtime

Here is the minimal command to interact with the GCE runtime:
```bash
opsmate chat --shell-command-runtime gce \
  --runtime-gce-instance <instance-name> \
  --runtime-gce-zone <zone> \
```

Here is an e2e interaction with the GCE runtime:

{{ asciinema("/assets/gce-runtime.cast") }}

In the example I am interacting with a GCE instance called `my-vm` in the `europe-west1-c` zone running inside a VPC without any public IP address. Opsmate uses the `gcloud compute ssh` command to connect to the instance with the help from [IAP tunneling](https://cloud.google.com/iap/docs/using-tcp-forwarding).

### Step 7: Cleanup

```bash
opsmate uninstall -y opsmate-runtime-gce

# Delete the GCE instance
gcloud compute instances delete my-vm --zone=$ZONE

# Delete the firewall rule
gcloud compute firewall-rules delete allow-ssh
```

## See also

- [Cookbook - Manage VMs](../cookbooks/manage-vms.md)
