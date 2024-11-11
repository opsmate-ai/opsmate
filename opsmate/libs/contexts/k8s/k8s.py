from opsmate.libs.core.contexts import (
    Context,
    ContextSpec,
    Metadata,
    Executable,
    ExecShell,
)
from opsmate.libs.core.contexts import os_ctx
import shutil
import subprocess

tools = ["kubectl", "helm", "kubectx", "kubens", "base64"]


class KubeCommands(Executable):
    def __call__(self, *args, **kwargs):
        return [tool for tool in tools if shutil.which(tool)]


class KubeContext(Executable):
    def __call__(self, *args, **kwargs):
        output = subprocess.run(
            ["kubectl", "config", "get-contexts"], capture_output=True
        )
        return output.stdout.decode()


class Namespaces(Executable):
    def __call__(self, *args, **kwargs):
        output = subprocess.run(["kubectl", "get", "ns"], capture_output=True)
        return output.stdout.decode()


k8s_ctx = Context(
    metadata=Metadata(
        name="k8s",
        labels={"type": "platform"},
        description="Kubernetes CLI specialist",
    ),
    spec=ContextSpec(
        params={},
        contexts=[os_ctx],
        helpers={
            "kube_commands": KubeCommands(),
            "kube_contexts": KubeContext(),
            "kube_namespaces": Namespaces(),
        },
        executables=[ExecShell],
        data="""
You are a kubernetes cluster administrator.

Here are the available commands to use:
{{ kube_commands()}}

Here are the contexts available:
{{ kube_contexts() }}

Here are the namespaces available:
{{ kube_namespaces() }}

A few things to keep in mind:
- When you do `kubectl logs ...` do not log more than 50 lines.
- When you execute `kubectl exec -it ...` use /bin/sh instead of bash.
- Always make sure that you are using the right context and namespace. For example never do `kuebctl get po xxx` without specifying the namespace
""",
    ),
)
