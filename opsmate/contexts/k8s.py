from opsmate.tools import (
    ShellCommand,
    KnowledgeRetrieval,
    ACITool,
    HtmlToText,
    PrometheusTool,
    Thinking,
)
from opsmate.dino.context import context
from opsmate.runtime import Runtime
from jinja2 import Template


@context(
    name="k8s",
    tools=[
        ShellCommand,
        KnowledgeRetrieval,
        ACITool,
        HtmlToText,
        PrometheusTool,
        Thinking,
    ],
)
async def k8s_ctx(runtimes: dict[str, Runtime] = {}) -> str:
    """Kubernetes SME"""

    # Pre-fetch all runtime information asynchronously
    k8s_info = {}
    if runtimes and "ShellCommand" in runtimes:
        k8s_info = {
            "kube_contexts": await __kube_contexts(runtimes),
            "namespaces": await __namespaces(runtimes),
        }
    else:
        raise ValueError("ShellCommand runtime not found")

    template = Template(
        """
<assistant>
You are a world class SRE who is an expert in kubernetes. You are tasked to help with kubernetes related problem solving
</assistant>

<important>
- When you do `kubectl logs ...` do not log more than 50 lines.
- When you look into any issues scoped to the namespaces, look into the events in the given namespaces.
- Always use `kubectl get --show-labels` for querying resources when `-ojson` or `-oyaml` are not being used.
- When running kubectl, always make sure that you are using the right context and namespace. For example never do `kuebctl get po xxx` without specifying the namespace.
- Never run interactive commands that cannot automatically exit, such as `vim`, `view`, `tail -f`, or `less`.
- Always include the `-y` flag with installation commands like `apt-get install` or `apt-get update` to prevent interactive prompts.
- Avoid any command that requires user input after execution.
- When it's unclear what causes error from the logs, you can view the k8s resources to have a holistic view of the situation.
- DO NOT create resources using `kubectl apply -f - <<EOF` or `echo ... | kubectl apply -f -` as this is extremely error prone.
</important>

<available_k8s_contexts>
{{ k8s_info.kube_contexts }}
</available_k8s_contexts>

<available_namespaces>
{{ k8s_info.namespaces }}
</available_namespaces>

<available_command_line_tools>
- kubectl
- helm
- and all the conventional command line tools such as grep, awk, wc, etc.
</available_command_line_tools>
    """
    )

    rendered_template = template.render(k8s_info=k8s_info)
    return rendered_template


async def __namespaces(runtimes: dict[str, Runtime]) -> str:
    return await runtimes["ShellCommand"].run(
        "kubectl get ns -o jsonpath='{.items[*].metadata.name}'"
    )


async def __kube_contexts(runtimes: dict[str, Runtime]) -> str:
    return await runtimes["ShellCommand"].run("kubectl config get-contexts")
