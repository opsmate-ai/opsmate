import os
import asyncio
from opsmate.runtime.local import LocalRuntime
from tempfile import NamedTemporaryFile
from opsmate.runtime.runtime import register_runtime


@register_runtime("docker")
class DockerRuntime(LocalRuntime):
    """Docker runtime allows model to execute tool calls within a docker container."""

    def __init__(
        self,
        container_name: str,
        envvars: dict = {},
        shell_cmd: str = "/bin/bash",
    ):
        self.container_name = container_name
        # write the envvars to a tmp file
        with NamedTemporaryFile(delete=False) as f:
            for key, value in envvars.items():
                f.write(f"{key}={value}\n")
                f.flush()
            self.envvars_file = f.name
        shell_cmd = f"docker exec --env-file {self.envvars_file} -i {self.container_name} {shell_cmd}"
        super().__init__(shell_cmd=shell_cmd, envvars=envvars)

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
