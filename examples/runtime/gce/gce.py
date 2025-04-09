import os
import asyncio
from opsmate.runtime.runtime import (
    register_runtime,
    RuntimeConfig,
    RuntimeError,
    co,
)
from opsmate.runtime.local import LocalRuntime
from pydantic import Field, ConfigDict
from typing import List
import structlog


logger = structlog.get_logger(__name__)


class GCERuntimeConfig(RuntimeConfig):
    model_config = ConfigDict(populate_by_name=True)

    instance_name: str = Field(alias="RUNTIME_GCE_INSTANCE", default="")
    zone: str = Field(alias="RUNTIME_GCE_ZONE", default="")
    project: str = Field(alias="RUNTIME_GCE_PROJECT", default="")
    username: str = Field(alias="RUNTIME_GCE_USERNAME", default="")
    use_iap: bool = Field(default=True, alias="RUNTIME_GCE_USE_IAP")
    iap_tunnel_options: List[str] = Field(default=[], alias="RUNTIME_GCE_IAP_OPTIONS")
    shell_cmd: str = Field(default="/bin/bash", alias="RUNTIME_GCE_SHELL")
    timeout: int = Field(default=20, alias="RUNTIME_GCE_TIMEOUT")
    connect_retries: int = Field(default=3, alias="RUNTIME_GCE_CONNECT_RETRIES")
    gcloud_binary: str = Field(default="gcloud", alias="RUNTIME_GCE_GCLOUD_BINARY")
    extra_flags: List[str] = Field(default=[], alias="RUNTIME_GCE_EXTRA_FLAGS")


@register_runtime("gce", GCERuntimeConfig)
class GCERuntime(LocalRuntime):
    """GCE runtime allows model to execute tool calls on a GCE instance using gcloud compute ssh."""

    def __init__(self, config: GCERuntimeConfig):
        self.instance_name = config.instance_name
        self.zone = config.zone
        self.project = config.project
        self.username = config.username
        self.use_iap = config.use_iap
        self.iap_tunnel_options = config.iap_tunnel_options
        self.shell_cmd = config.shell_cmd
        self.timeout = config.timeout
        self.connect_retries = config.connect_retries
        self.gcloud_binary = config.gcloud_binary
        self.extra_flags = config.extra_flags

        self._lock = asyncio.Lock()
        self.process = None
        self.connected = False

    async def _build_ssh_command(self):
        """Build the gcloud compute ssh command with appropriate options."""
        ssh_cmd = [self.gcloud_binary, "compute", "ssh"]

        # Add instance name with username if specified
        if self.username:
            ssh_cmd.append(f"{self.username}@{self.instance_name}")
        else:
            ssh_cmd.append(self.instance_name)

        # Add zone if specified
        if self.zone:
            ssh_cmd.extend(["--zone", self.zone])

        if self.project:
            ssh_cmd.extend(["--project", self.project])

        # Add IAP tunnel support (default)
        if self.use_iap:
            ssh_cmd.append("--tunnel-through-iap")

            # Add any additional IAP tunnel options
            if self.iap_tunnel_options:
                ssh_cmd.extend(self.iap_tunnel_options)

        # Add quiet mode to suppress unnecessary output
        ssh_cmd.append("--quiet")

        # Add any extra flags
        if self.extra_flags:
            ssh_cmd.extend(self.extra_flags)

        return ssh_cmd

    async def _start_shell(self):
        """Start an interactive GCE shell session."""
        if (
            not self.process
            or self.process.returncode is not None
            or not self.connected
        ):
            ssh_cmd = await self._build_ssh_command()

            # Add the shell command
            cmd = " ".join(ssh_cmd) + f" --command '{self.shell_cmd}'"

            # Start the GCE SSH process
            self.process = await asyncio.create_subprocess_shell(
                cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            self.connected = True

        return self.process

    async def connect(self):
        """Connect to the GCE instance with retry logic."""
        for attempt in range(self.connect_retries):
            try:
                # Test connection first
                ssh_cmd = await self._build_ssh_command()
                test_cmd = ssh_cmd + ["--command", "echo 'Connection successful'"]
                exit_code, output = co(test_cmd, timeout=self.timeout, env=os.environ)

                if exit_code != 0:
                    logger.warning(
                        f"GCE connection attempt {attempt+1} failed", output=output
                    )
                    if attempt == self.connect_retries - 1:
                        raise RuntimeError(
                            f"Failed to connect to GCE instance", output=output
                        )
                    await asyncio.sleep(2)
                else:
                    logger.info("GCE connection successful")
                    break
            except Exception as e:
                logger.warning(
                    f"GCE connection attempt {attempt+1} failed with exception",
                    error=str(e),
                )
                if attempt == self.connect_retries - 1:
                    raise RuntimeError(f"Failed to connect to GCE instance: {str(e)}")
                await asyncio.sleep(2)

        await self._start_shell()

    async def disconnect(self):
        """Disconnect from the GCE instance and clean up resources."""
        if self.process and self.process.returncode is None:
            try:
                self.process.terminate()
                self.process._transport.close()
            except Exception as e:
                logger.warning(f"Error disconnecting from GCE instance: {str(e)}")
            finally:
                self.process = None
                self.connected = False

    async def os_info(self):
        """Get OS information from the remote GCE instance."""
        return await self.run("cat /etc/os-release")

    async def whoami(self):
        """Get current user information from the remote GCE instance."""
        return await self.run("whoami")

    async def has_systemd(self):
        """Check if the remote GCE instance uses systemd."""
        return await self.run(
            "[[ $(command -v systemctl) ]] && echo 'has systemd' || echo 'no systemd'"
        )

    async def runtime_info(self):
        """Return information about the GCE runtime."""
        return f"""GCE runtime
Connected to instance: {self.instance_name} {f'(zone: {self.zone})' if self.zone else ''} {f'(project: {self.project})' if self.project else ''}
IAP tunneling: {'enabled' if self.use_iap else 'disabled'}
Use 'sudo' for privileged operations if you have sudo access.
"""
