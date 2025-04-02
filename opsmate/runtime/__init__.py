from opsmate.runtime.runtime import Runtime, RuntimeError, discover_runtimes
from opsmate.runtime.local import LocalRuntime
from opsmate.runtime.docker import DockerRuntime
from opsmate.runtime.ssh import SSHRuntime
from opsmate.runtime.k8s import K8sRuntime

__all__ = [
    "Runtime",
    "LocalRuntime",
    "RuntimeError",
    "DockerRuntime",
    "SSHRuntime",
    "K8sRuntime",
]

discover_runtimes()
