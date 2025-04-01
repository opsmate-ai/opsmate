from opsmate.runtime.runtime import Runtime, RuntimeError, discover_runtimes
from opsmate.runtime.local import LocalRuntime
from opsmate.runtime.docker import DockerRuntime
from opsmate.runtime.ssh import SSHRuntime

__all__ = ["Runtime", "LocalRuntime", "RuntimeError", "DockerRuntime", "SSHRuntime"]

discover_runtimes()
