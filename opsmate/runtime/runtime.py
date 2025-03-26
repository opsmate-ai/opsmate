from abc import ABC, abstractmethod
import asyncio


class Runtime(ABC):
    @abstractmethod
    async def run(self, *args, **kwargs):
        pass

    @abstractmethod
    async def connect(self):
        pass

    @abstractmethod
    async def disconnect(self):
        pass


class RuntimeError(Exception): ...


class LocalRuntime(Runtime):
    def __init__(self, shell_cmd="/bin/bash"):
        self._lock = asyncio.Lock()
        self.process = None
        self.connected = False
        self.shell_cmd = shell_cmd

    async def connect(self):
        await self._start_shell()

    async def _start_shell(self, shell_cmd="/bin/bash"):
        if (
            not self.process
            or self.process.returncode is not None
            or not self.connected
        ):
            self.process = await asyncio.create_subprocess_shell(
                shell_cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            self.connected = True
        return self.process

    async def disconnect(self):
        if self.process and self.process.returncode is None:
            self.process.terminate()
            self.process._transport.close()
            self.connected = False

    async def run(
        self, command: str, envvars: dict[str, str] = {}, timeout: float = 120.0
    ):
        async with self._lock:
            try:
                if not self.connected:
                    await self._start_shell()

                # Set environment variables if needed
                env_commands = []
                for key, value in envvars.items():
                    env_commands.append(f"export {key}={value}")

                if env_commands:
                    env_setup = "; ".join(env_commands) + "; "
                    full_command = env_setup + command
                else:
                    full_command = command

                # Add a unique marker to identify end of output
                marker = f"__END_OF_COMMAND_{id(command)}__"
                full_command = f"{full_command}; echo '{marker}'\n"

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
