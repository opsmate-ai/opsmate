import os
import asyncio
from opsmate.runtime.local import LocalRuntime
from tempfile import NamedTemporaryFile
from opsmate.runtime.runtime import register_runtime, RuntimeConfig
from pydantic import Field, ConfigDict
from typing import Dict


class DockerRuntimeConfig(RuntimeConfig):
    model_config = ConfigDict(populate_by_name=True)

    container_name: str = Field(alias="RUNTIME_DOCKER_CONTAINER_NAME")
    shell_cmd: str = Field(default="/bin/bash", alias="RUNTIME_DOCKER_SHELL")
    envvars: Dict[str, str] = Field(default={}, alias="RUNTIME_DOCKER_ENV")


@register_runtime("docker", DockerRuntimeConfig)
class DockerRuntime(LocalRuntime):
    """Docker runtime allows model to execute tool calls within a docker container."""

    def __init__(self, config: DockerRuntimeConfig):
        self.container_name = config.container_name

        with NamedTemporaryFile(delete=False) as f:
            for key, value in config.envvars.items():
                f.write(f"{key}={value}\n")
                f.flush()
            self.envvars_file = f.name

        shell_cmd = f"docker exec --env-file {self.envvars_file} -i {self.container_name} {config.shell_cmd}"

        self._lock = asyncio.Lock()
        self.process = None
        self.connected = False
        self.shell_cmd = shell_cmd

    async def _start_shell(self):
        if (
            not self.process
            or self.process.returncode is not None
            or not self.connected
        ):
            self.process = await asyncio.create_subprocess_shell(
                self.shell_cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            self.connected = True
        return self.process

    async def disconnect(self):
        os.remove(self.envvars_file)
        await super().disconnect()
