import os
import asyncio
from opsmate.runtime.local import LocalRuntime
from tempfile import NamedTemporaryFile
from opsmate.runtime.runtime import register_runtime, RuntimeConfig, RuntimeError, co
from pydantic import Field
from typing import Dict
import structlog


logger = structlog.get_logger(__name__)


class DockerRuntimeConfig(RuntimeConfig):
    container_name: str = Field(alias="RUNTIME_DOCKER_CONTAINER_NAME", default="")
    shell_cmd: str = Field(default="/bin/bash", alias="RUNTIME_DOCKER_SHELL")
    envvars: Dict[str, str] = Field(default={}, alias="RUNTIME_DOCKER_ENV")

    compose_file: str = Field(
        default="docker-compose.yml",
        alias="RUNTIME_DOCKER_COMPOSE_FILE",
        description="Path to the docker compose file",
    )
    service_name: str = Field(
        default="default",
        alias="RUNTIME_DOCKER_SERVICE_NAME",
        description="Name of the service to run",
    )


@register_runtime("docker", DockerRuntimeConfig)
class DockerRuntime(LocalRuntime):
    """Docker runtime allows model to execute tool calls within a docker container."""

    def __init__(self, config: DockerRuntimeConfig):
        self.container_name = config.container_name

        with NamedTemporaryFile(mode="w", delete=False) as f:
            for key, value in config.envvars.items():
                f.write(f"{key}={value}\n")
                f.flush()
            self.envvars_file = f.name

        self._lock = asyncio.Lock()
        self.process = None
        self.connected = False

        self.from_compose = False
        self.from_container = False
        self.from_config(config)

    def _from_compose(self, config: DockerRuntimeConfig):
        if not os.path.exists(config.compose_file):
            logger.error(
                f"Docker compose file not found", compose_file=config.compose_file
            )
            raise RuntimeError(f"Docker compose file {config.compose_file} not found")

        async def bootstrap():
            exit_code, output = co(
                [
                    "docker",
                    "compose",
                    "-f",
                    config.compose_file,
                    "--env-file",
                    self.envvars_file,
                    "up",
                    "-d",
                ]
            )
            if exit_code != 0:
                raise RuntimeError(f"Failed to start docker container", output=output)
            logger.info(f"Started docker container", output=output)

            # check if service name exists
            exit_code, output = co(
                [
                    "docker",
                    "compose",
                    "-f",
                    config.compose_file,
                    "ps",
                    "--services",
                ]
            )
            if exit_code != 0:
                raise RuntimeError(
                    f"Failed to check if service name exists", output=output
                )

            if config.service_name not in output:
                raise RuntimeError(
                    f"Service {config.service_name} not found",
                    output=output,
                )

        self.bootstrap = bootstrap

        self.shell_cmd = f"docker compose -f {config.compose_file} exec {config.service_name} {config.shell_cmd}"

        self.from_compose = True

    def _from_container(self, config: DockerRuntimeConfig):
        async def bootstrap():
            exit_code, output = co(["docker", "start", self.container_name])
            if exit_code != 0:
                raise RuntimeError(f"Failed to start docker container", output=output)
            logger.info(f"Started docker container", output=output)

        self.bootstrap = bootstrap
        self.shell_cmd = f"docker exec --env-file {self.envvars_file} -i {self.container_name} {config.shell_cmd}"
        self.from_container = True

    def from_config(self, config: DockerRuntimeConfig):
        if config.container_name != "":
            self._from_container(config)
        else:
            self._from_compose(config)

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

    async def connect(self):
        if self.bootstrap:
            await self.bootstrap()

        await self._start_shell()

    async def disconnect(self):
        os.remove(self.envvars_file)
        await super().disconnect()

    async def os_info(self):
        return await self.run("cat /etc/os-release")

    async def whoami(self):
        return await self.run("whoami")

    async def has_systemd(self):
        return await self.run(
            "[[ $(command -v systemctl) ]] && echo 'has systemd' || echo 'no systemd'"
        )

    async def runtime_info(self):
        return """docker runtime
Use `DEBIAN_FRONTEND=noninteractive TZ=Etc/UTC` for package management in Debian/Ubuntu based containers.
        """
