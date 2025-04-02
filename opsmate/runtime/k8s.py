import os
import asyncio
from opsmate.runtime.local import LocalRuntime
from opsmate.runtime.runtime import register_runtime, RuntimeConfig, RuntimeError, co
from pydantic import Field
from typing import Optional
import structlog


logger = structlog.get_logger(__name__)


class K8sRuntimeConfig(RuntimeConfig):
    namespace: str = Field(alias="RUNTIME_K8S_NAMESPACE", default="default")
    pod_name: str = Field(alias="RUNTIME_K8S_POD", default="")
    container_name: Optional[str] = Field(
        alias="RUNTIME_K8S_CONTAINER",
        default=None,
        description="Name of the container of the pod, if not specified, the first container will be used",
    )
    shell_cmd: str = Field(default="/bin/sh", alias="RUNTIME_K8S_SHELL")


@register_runtime("k8s", K8sRuntimeConfig)
class K8sRuntime(LocalRuntime):
    """Kubernetes runtime allows model to execute tool calls within a Kubernetes pod."""

    def __init__(self, config: K8sRuntimeConfig):
        self.namespace = config.namespace
        self.pod_name = config.pod_name
        self.container_name = config.container_name
        self.shell_cmd = config.shell_cmd

        self._lock = asyncio.Lock()
        self.process = None
        self.connected = False

    async def _start_shell(self):
        if (
            not self.process
            or self.process.returncode is not None
            or not self.connected
        ):
            container_arg = f"-c {self.container_name}" if self.container_name else ""
            kubectl_cmd = f"kubectl exec -n {self.namespace} {self.pod_name} {container_arg} -i -- {self.shell_cmd}"

            self.process = await asyncio.create_subprocess_shell(
                kubectl_cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            self.connected = True
        return self.process

    async def connect(self):
        # Verify pod exists and is running
        container_arg = f"-c {self.container_name}" if self.container_name else ""
        exit_code, output = co(
            [
                "kubectl",
                "get",
                "pod",
                "-n",
                self.namespace,
                self.pod_name,
                "-o",
                "jsonpath={.status.phase}",
            ]
        )

        if exit_code != 0:
            raise RuntimeError(f"Failed to get pod status", output=output)

        if output.strip() != "Running":
            raise RuntimeError(f"Pod is not running", status=output)

        # Check if container exists if specified
        if self.container_name:
            exit_code, output = co(
                [
                    "kubectl",
                    "get",
                    "pod",
                    "-n",
                    self.namespace,
                    self.pod_name,
                    "-o",
                    f"jsonpath={{.spec.containers[?(@.name=='{self.container_name}')].name}}",
                ]
            )

            if exit_code != 0 or not output.strip():
                raise RuntimeError(
                    f"Container {self.container_name} not found in pod", output=output
                )
        else:
            # Get the first container name
            exit_code, output = co(
                [
                    "kubectl",
                    "get",
                    "pod",
                    "-n",
                    self.namespace,
                    self.pod_name,
                    "-o",
                    "jsonpath={.spec.containers[0].name}",
                ]
            )

            if exit_code != 0 or not output.strip():
                raise RuntimeError(f"Failed to get first container name", output=output)

            self.container_name = output.strip()

        # Get the image name
        exit_code, output = co(
            [
                "kubectl",
                "get",
                "pod",
                "-n",
                self.namespace,
                self.pod_name,
                "-o",
                f"jsonpath={{.spec.containers[?(@.name=='{self.container_name}')].image}}",
            ]
        )

        if exit_code != 0 or not output.strip():
            raise RuntimeError(f"Failed to get image name", output=output)

        self.image = output.strip()

        logger.info(
            "Connected to pod",
            namespace=self.namespace,
            pod=self.pod_name,
            container=self.container_name,
            image=self.image,
        )

        await self._start_shell()

    async def disconnect(self):
        await super().disconnect()

    async def os_info(self):
        return await self._run_cmd("cat /etc/os-release")

    async def whoami(self):
        return await self._run_cmd("whoami")

    async def has_systemd(self):
        return await self._run_cmd(
            "[[ $(command -v systemctl) ]] && echo 'has systemd' || echo 'no systemd'"
        )

    async def _run_cmd(self, cmd: str):
        try:
            return await self.run(cmd)
        except RuntimeError as e:
            return "Unknown"

    async def runtime_info(self):
        return f"""Current pod environment:
Namespace: {self.namespace}
Pod: {self.pod_name}
Container: {self.container_name if self.container_name else "default"}
Image: {self.image}
"""
