import os
import asyncio
from opsmate.runtime.local import LocalRuntime
from tempfile import NamedTemporaryFile
from opsmate.runtime.runtime import register_runtime, RuntimeConfig, RuntimeError, co
from pydantic import Field, ConfigDict
from typing import Dict, Optional

import structlog


logger = structlog.get_logger(__name__)


class SSHRuntimeConfig(RuntimeConfig):
    host: str = Field(alias="RUNTIME_SSH_HOST", default="")
    port: int = Field(default=22, alias="RUNTIME_SSH_PORT")
    username: str = Field(alias="RUNTIME_SSH_USERNAME", default="")
    password: Optional[str] = Field(default=None, alias="RUNTIME_SSH_PASSWORD")
    key_file: Optional[str] = Field(default=None, alias="RUNTIME_SSH_KEY_FILE")
    shell_cmd: str = Field(default="/bin/bash", alias="RUNTIME_SSH_SHELL")
    # envvars: Dict[str, str] = Field(default={}, alias="RUNTIME_SSH_ENV")
    timeout: int = Field(default=10, alias="RUNTIME_SSH_TIMEOUT")
    connect_retries: int = Field(default=3, alias="RUNTIME_SSH_CONNECT_RETRIES")


@register_runtime("ssh", SSHRuntimeConfig)
class SSHRuntime(LocalRuntime):
    """SSH runtime allows model to execute tool calls on a remote server via SSH."""

    def __init__(self, config: SSHRuntimeConfig):
        self.host = config.host
        self.port = config.port
        self.username = config.username
        self.password = config.password
        self.key_file = config.key_file
        self.shell_cmd = config.shell_cmd
        self.timeout = config.timeout
        self.connect_retries = config.connect_retries

        # Create a temporary file to store environment variables
        # with NamedTemporaryFile(mode="w", delete=False) as f:
        #     for key, value in config.envvars.items():
        #         f.write(f'export {key}="{value}"\n')
        #     self.envvars_file = f.name

        self._lock = asyncio.Lock()
        self.process = None
        self.connected = False

    async def _build_ssh_command(self):
        """Build the SSH command with appropriate options."""
        ssh_cmd = ["ssh"]

        # Add port option
        ssh_cmd.extend(["-p", str(self.port)])

        # Add key file if specified
        if self.key_file:
            ssh_cmd.extend(["-i", self.key_file])

        # Add common SSH options
        ssh_cmd.extend(
            ["-o", "StrictHostKeyChecking=no", "-o", f"ConnectTimeout={self.timeout}"]
        )

        # Add host with username
        ssh_cmd.append(f"{self.username}@{self.host}")

        return ssh_cmd

    async def _start_shell(self):
        """Start an interactive SSH shell session."""
        if (
            not self.process
            or self.process.returncode is not None
            or not self.connected
        ):
            ssh_cmd = await self._build_ssh_command()
            cmd = " ".join(ssh_cmd) + f" {self.shell_cmd}"

            # Start the SSH process
            self.process = await asyncio.create_subprocess_shell(
                cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            self.connected = True

        return self.process

    async def connect(self):
        """Connect to the SSH server with retry logic."""
        for attempt in range(self.connect_retries):
            try:
                # Test connection first
                ssh_cmd = await self._build_ssh_command()
                test_cmd = ssh_cmd + ["echo 'Connection successful'"]
                exit_code, output = co(test_cmd, timeout=self.timeout, env=os.environ)

                if exit_code != 0:
                    logger.warning(
                        f"SSH connection attempt {attempt+1} failed", output=output
                    )
                    if attempt == self.connect_retries - 1:
                        raise RuntimeError(
                            f"Failed to connect to SSH server", output=output
                        )
                    await asyncio.sleep(2)
                else:
                    logger.info("SSH connection successful")
                    break
            except Exception as e:
                logger.warning(
                    f"SSH connection attempt {attempt+1} failed with exception",
                    error=str(e),
                )
                if attempt == self.connect_retries - 1:
                    raise RuntimeError(f"Failed to connect to SSH server: {str(e)}")
                await asyncio.sleep(2)

        # Upload environment variables file if any variables were defined
        # if os.path.getsize(self.envvars_file) > 0:
        #     remote_envfile = f"/tmp/opsmate_env_{os.path.basename(self.envvars_file)}"
        #     scp_cmd = ["scp", "-P", str(self.port), "-o", "StrictHostKeyChecking=no"]

        #     if self.key_file:
        #         scp_cmd.extend(["-i", self.key_file])

        #     scp_cmd.extend(
        #         [self.envvars_file, f"{self.username}@{self.host}:{remote_envfile}"]
        #     )

        #     exit_code, output = co(scp_cmd)
        #     if exit_code != 0:
        #         raise RuntimeError(
        #             f"Failed to upload environment variables file", output=output
        #         )

        #     # Source the environment file
        #     source_cmd = await self._build_ssh_command()
        #     source_cmd.extend([f"echo 'source {remote_envfile}' >> ~/.bashrc"])
        #     co(source_cmd)

        await self._start_shell()

    async def disconnect(self):
        """Disconnect from the SSH server and clean up resources."""
        # os.remove(self.envvars_file)
        await super().disconnect()

    async def os_info(self):
        """Get OS information from the remote server."""
        return await self.run("cat /etc/os-release")

    async def whoami(self):
        """Get current user information from the remote server."""
        return await self.run("whoami")

    async def has_systemd(self):
        """Check if the remote server uses systemd."""
        return await self.run(
            "[[ $(command -v systemctl) ]] && echo 'has systemd' || echo 'no systemd'"
        )

    async def runtime_info(self):
        """Return information about the SSH runtime."""
        return f"""ssh runtime
Connected to: {self.username}@{self.host}:{self.port}
Use 'sudo' for privileged operations if you have sudo access.
Environment variables can be set through the configuration.
"""
