from opsmate.runtime.runtime import (
    Runtime,
    RuntimeError,
    register_runtime,
    RuntimeConfig,
)
from pydantic import Field
import asyncio
from typing import Dict


class LocalRuntimeConfig(RuntimeConfig):
    shell_cmd: str = Field(default="/bin/bash", alias="RUNTIME_LOCAL_SHELL")
    envvars: Dict[str, str] = Field(default={}, alias="RUNTIME_LOCAL_ENV")


@register_runtime("local", LocalRuntimeConfig)
class LocalRuntime(Runtime):
    """Local runtime allows model to execute tool calls within the same namespace as the opsmate process."""

    def __init__(self, config: LocalRuntimeConfig = LocalRuntimeConfig()):
        self._lock = asyncio.Lock()
        self.process = None
        self.connected = False
        self.shell_cmd = config.shell_cmd
        self.envvars = config.envvars

    async def connect(self):
        await self._start_shell()

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
                env=self.envvars,
            )
            self.connected = True
        return self.process

    async def disconnect(self):
        if self.process and self.process.returncode is None:
            self.process.terminate()
            self.process._transport.close()
            self.connected = False

    async def run(self, command: str, timeout: float = 120.0):
        async with self._lock:
            try:
                if not self.connected:
                    await self._start_shell()
                # Add a unique marker to identify end of output
                marker = f"__END_OF_COMMAND_{id(command)}__"
                full_command = f"{command}; echo '{marker}'\n"

                # Send command to the shell
                self.process.stdin.write(full_command.encode())
                await self.process.stdin.drain()

                # Read output until we see our marker
                output = []

                async def read_until_marker():
                    while True:
                        line = await self.process.stdout.readline()
                        line_str = line.decode().rstrip("\n")
                        if line_str == marker:
                            break
                        output.append(line_str)

                await asyncio.wait_for(read_until_marker(), timeout=timeout)
                return "\n".join(output)

            except Exception as e:
                raise RuntimeError(f"Error running command: {e}") from e
