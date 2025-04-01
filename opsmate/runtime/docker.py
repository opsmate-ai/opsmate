import os
import asyncio
from opsmate.runtime.local import LocalRuntime
from tempfile import NamedTemporaryFile
from opsmate.runtime.runtime import register_runtime, RuntimeConfig, RuntimeError
from pydantic import Field, ConfigDict
from typing import Dict
import structlog
import subprocess

logger = structlog.get_logger(__name__)


def co(cmd, **kwargs):
    """
    Check output of a command.
    Return the exit code and output of the command.
    """
    kwargs["stderr"] = subprocess.STDOUT
    try:
        output = subprocess.check_output(cmd, **kwargs).strip()
        return 0, output
    except subprocess.CalledProcessError as e:
        return e.returncode, e.output


class DockerRuntimeConfig(RuntimeConfig):
    model_config = ConfigDict(populate_by_name=True)

    container_name: str = Field(alias="RUNTIME_DOCKER_CONTAINER_NAME", default="")
    shell_cmd: str = Field(default="/bin/bash", alias="RUNTIME_DOCKER_SHELL")
    envvars: Dict[str, str] = Field(default={}, alias="RUNTIME_DOCKER_ENV")

    # image_name: str = Field(
    #     default="",
    #     alias="RUNTIME_DOCKER_IMAGE_NAME",
    #     description="Name of the image to run",
    # )

    # entrypoint: str = Field(
    #     default="sleep",
    #     alias="RUNTIME_DOCKER_ENTRYPOINT",
    #     description="Entrypoint to run the container",
    # )

    # cmd: str = Field(
    #     default="infinity",
    #     alias="RUNTIME_DOCKER_CMD",
    #     description="Command to start the container",
    # )

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
        self.from_config(config)

    def _from_compose(self, config: DockerRuntimeConfig):
        if not os.path.exists(config.compose_file):
            logger.error(
                f"Docker compose file not found", compose_file=config.compose_file
            )
            return None

        self.bootstrap = [
            "docker",
            "compose",
            "-f",
            config.compose_file,
            "--env-file",
            self.envvars_file,
            "up",
            "-d",
        ]

        self.shell_cmd = f"docker compose -f {config.compose_file} exec {config.service_name} {config.shell_cmd}"
        self.from_compose = True

    # def _from_image(self, config: DockerRuntimeConfig):
    #     if config.image_name == "":
    #         logger.error(f"Docker image name not found", image_name=config.image_name)
    #         return None

    #     self.container_name = f"opsmate-{uuid.uuid4()}"
    #     cmd = [
    #         "docker",
    #         "run",
    #         "-d",
    #         "--rm",
    #         "--name",
    #         self.container_name,
    #         "--entrypoint",
    #         config.entrypoint,
    #         config.image_name,
    #         config.cmd,
    #     ]
    #     output = co(
    #         cmd,
    #         text=True,
    #     ).strip()
    #     print(output)
    #     self.shell_cmd = f"docker exec --env-file {self.envvars_file} -i {self.container_name} {config.shell_cmd}"
    #     self.from_image = True

    def _from_container(self, config: DockerRuntimeConfig):
        self.bootstrap = [
            "docker",
            "start",
            self.container_name,
        ]
        self.shell_cmd = f"docker exec --env-file {self.envvars_file} -i {self.container_name} {config.shell_cmd}"
        self.from_container = True

    def from_config(self, config: DockerRuntimeConfig):
        if config.container_name != "":
            self._from_container(config)
        # elif config.image_name != "":
        #     self._from_image(config)
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
            exit_code, output = co(self.bootstrap)
            if exit_code != 0:
                raise RuntimeError(f"Failed to start docker container", output=output)

        await super().connect()

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
