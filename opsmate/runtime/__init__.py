from opsmate.runtime.runtime import Runtime, RuntimeError, discover_runtimes
from opsmate.runtime.local import LocalRuntime

__all__ = ["Runtime", "LocalRuntime", "RuntimeError"]

discover_runtimes()
