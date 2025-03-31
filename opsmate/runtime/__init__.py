from opsmate.runtime.runtime import Runtime, RuntimeError, discover_runtimes
from opsmate.runtime.local import LocalRuntime
from opsmate.runtime.docker import DockerRuntime

__all__ = ["Runtime", "LocalRuntime", "RuntimeError", "DockerRuntime"]

discover_runtimes()
