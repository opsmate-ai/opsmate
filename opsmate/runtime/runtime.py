from abc import ABC, abstractmethod
from typing import Type, List
from opsmate.libs.config.base_settings import BaseSettings
import pkg_resources
import structlog
import subprocess
import traceback

logger = structlog.get_logger(__name__)


class RuntimeConfig(BaseSettings): ...


class Runtime(ABC):
    runtimes: dict[str, Type["Runtime"]] = {}
    configs: dict[str, Type[RuntimeConfig]] = {}

    @abstractmethod
    async def run(self, *args, **kwargs):
        pass

    @abstractmethod
    async def connect(self):
        pass

    @abstractmethod
    async def disconnect(self):
        pass

    @abstractmethod
    async def os_info(self):
        pass

    @abstractmethod
    async def whoami(self):
        pass

    @abstractmethod
    async def runtime_info(self):
        pass

    @abstractmethod
    async def has_systemd(self):
        pass


class RuntimeError(Exception):
    """
    Exception raised when a runtime operation fails.
    """

    def __init__(self, message: str, output: str | None = None):
        self.message = message
        self.output = output
        super().__init__(self.message)

    def __str__(self):
        return f"{self.message}\n{self.output}"


def register_runtime(name: str, config: Type[RuntimeConfig]):
    def wrapper(cls: Type[Runtime]):
        Runtime.runtimes[name] = cls
        Runtime.configs[name] = config

        return cls

    return wrapper


def discover_runtimes(group_name="opsmate.runtime.runtimes"):
    for entry_point in pkg_resources.iter_entry_points(group_name):
        try:
            cls = entry_point.load()
            if not issubclass(cls, Runtime):
                logger.error(
                    "Runtime must inherit from the Runtime class", name=entry_point.name
                )
                continue
        except Exception as e:
            logger.error(
                "Error loading runtime",
                name=entry_point.name,
                error=e,
                traceback=traceback.format_exc(),
            )


def co(cmd, **kwargs):
    """
    Check output of a command.
    Return the exit code and output of the command.
    If timeout is specified, the command will be terminated after timeout seconds.
    Return code for timeout is 124 (consistent with the timeout command).
    """
    kwargs["stderr"] = subprocess.STDOUT
    kwargs["text"] = True

    try:
        output = subprocess.check_output(cmd, **kwargs).strip()
        return 0, output
    except subprocess.CalledProcessError as e:
        return e.returncode, e.output
    except subprocess.TimeoutExpired as e:
        return 124, e.stdout
