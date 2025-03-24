from braintrust import Eval, EvalHooks
from evals.scorers import OpsmateScorer, TextEditScorer
from opsmate.contexts import k8s_ctx
from opsmate.dino import run_react
from opsmate.dino.types import ReactAnswer
from opsmate.libs.core.trace import start_trace
from opsmate.libs.config import config
from opentelemetry import trace
import structlog
import os
import tempfile
import shutil

config.set_loglevel()
logger = structlog.get_logger(__name__)
tracer = trace.get_tracer("opsmate.eval")

project_name = "opsmate-eval"
project_id = os.getenv("BRAINTRUST_PROJECT_ID")

if os.getenv("BRAINTRUST_API_KEY") is not None:
    OTEL_EXPORTER_OTLP_ENDPOINT = "https://api.braintrust.dev/otel"
    OTEL_EXPORTER_OTLP_HEADERS = f"Authorization=Bearer {os.getenv('BRAINTRUST_API_KEY')}, x-bt-parent=project_id:{project_id}"

    os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = OTEL_EXPORTER_OTLP_ENDPOINT
    os.environ["OTEL_EXPORTER_OTLP_HEADERS"] = OTEL_EXPORTER_OTLP_HEADERS

    start_trace()


async def k8s_agent(question: str, hooks: EvalHooks):
    with tracer.start_as_current_span("eval_k8s_agent") as span:
        span.set_attribute("question", question)

        contexts = await k8s_ctx.resolve_contexts()
        tools = k8s_ctx.resolve_tools()
        async for output in run_react(
            question,
            contexts=contexts,
            tools=tools,
            model=hooks.metadata.get("model"),
        ):
            logger.info("output", output=output)

        if isinstance(output, ReactAnswer):
            return output.answer
        else:
            raise ValueError(f"Unexpected output type: {type(output)}")


simple_test_cases = [
    {
        "input": "how many pods are running in the cluster?",
        "expected": "there are {{pod_num}} pods running in the cluster",
        "tags": ["k8s", "simple"],
        "metadata": {
            "cmds": {
                "pod_num": "kubectl get pods -A --no-headers | wc -l",
            }
        },
    },
    {
        "input": "how many coredns pods are running in the cluster?",
        "expected": "there are {{coredns_num}} coredns pods running in the cluster",
        "tags": ["k8s", "simple"],
        "metadata": {
            "cmds": {
                "coredns_num": "kubectl get pods -A --no-headers | grep -i coredns | wc -l",
            }
        },
    },
    {
        "input": "how many nodes are running in the cluster?",
        "expected": "there are {{node_num}} nodes running in the cluster",
        "tags": ["k8s", "simple"],
        "metadata": {
            "cmds": {
                "node_num": "kubectl get nodes --no-headers | wc -l",
            }
        },
    },
    {
        "input": "list the name of namespaces in the cluster",
        "expected": "the namespaces in the cluster are {{namespaces}}",
        "tags": ["k8s", "simple"],
        "metadata": {
            "cmds": {
                "namespaces": "kubectl get namespaces --no-headers | awk '{print $1}'",
            }
        },
    },
    {
        "input": "what is the version of the kubernetes cluster?",
        "expected": "the version of the kubernetes cluster is {{version}}",
        "tags": ["k8s", "simple"],
        "metadata": {
            "cmds": {
                "version": """kubectl version | grep -i "Server Version" | awk '{print $3}'""",
            }
        },
    },
    {
        "input": "how to start an ephemeral ubuntu 24.04 pod in the cluster with interactive shell, return the command to run",
        "expected": "kubectl run ubuntu --image=ubuntu:24.04 --rm -ti -- bash",
        "tags": ["k8s", "simple"],
        "metadata": {},
    },
    {
        "input": "what RBAC permissions does content-manager-sa in the content ns have",
        "expected": "the `content-manager-sa` in the `content-service` namespace has get, list, watch access to pods and services in the `content-service` namespace, granted through the `content-reader` role.",
        "tags": ["k8s", "simple"],
        "metadata": {},
    },
]

investigation_test_cases = [
    {
        "input": "what is the issue with the finance-app deployment, please summarise the root cause in 2 sentences.",
        "expected": "the finance-app deployment is experiencing OOM (Out of Memory) kill errors, caused by the stress command from the polinux/stress image.",
        "tags": ["k8s", "investigation"],
        "metadata": {},
    },
    {
        "input": "why the ecomm-shop service is not running, please summarise the root cause in 2 sentences.",
        "expected": "the ecomm-shop service is not running due to misconfigured readiness probe.",
        "tags": ["k8s", "investigation"],
        "metadata": {},
    },
    {
        "input": "why the accounting software is not deployed, please summarise the root cause in 2 sentences.",
        "expected": "the accounting software is not deployed because it's not schedulable, due it is not tolerated to taint node-role.kubernetes.io/control-plane",
        "tags": ["k8s", "investigation"],
        "metadata": {},
    },
    {
        "input": "why the hr-app is not running, please summarise the root cause in 2 sentences.",
        "expected": "the hr-app is not running because the container image `do-not-exist-image:1.0.1` does not exist.",
        "tags": ["k8s", "investigation"],
        "metadata": {},
    },
    {
        "input": "why the innovation app is not ready? only investigate do not fix the issue, summarise the root cause in 2 sentences.",
        "expected": "the innovation app is not ready because of database connection issues. The `mysql-service` that is supposed to be used by the app does not exist.",
        "tags": ["k8s", "investigation"],
        "metadata": {},
    },
    {
        "input": "why the pod in the default namespace cannot access grafana service, please investigate and summarise the root cause in 2 sentences.",
        "expected": "This is because the network policy `monitoring/grafana` is blocking the access to the grafana service. It is only allows traffic from pods with `app.kubernetes.io/name=prometheus` label within the same `monitoring` namespace.",
        "tags": ["k8s", "investigation"],
        "metadata": {},
    },
    {
        "input": "what's wrong with the content-app service? Please investigate and summarize the root cause in 2 sentences.",
        "expected": "The content-manager pod is failing to access ConfigMaps and Secrets due to insufficient RBAC permissions. The service account only has permissions for pods and services, but lacks permissions for ConfigMaps and Secrets resources.",
        "tags": ["k8s", "investigation"],
        "metadata": {},
    },
    {
        "input": "The audit server in the audit namespace doesn't appear to be functioning correctly. Please investigate and summarize the root cause in a few sentences.",
        "expected": """
        The audit server is not functioning correctly because it is unable to connect to the MySQL database.
        This is due to the misconfigured matchLabels in the NetworkPolicy `audit/audit-server`.
        The matchLabels are `app: audit-app` instead of `app: audit-server`.
        """,
        "tags": ["k8s", "investigation"],
        "metadata": {},
    },
]

models = ["claude-3-7-sonnet-20250219", "gpt-4o"]
# models = ["gpt-4o"]
test_cases = [
    {
        **case,
        "tags": [model, *case["tags"]],
        "metadata": {"model": model, **case["metadata"]},
    }
    for model in models
    for case in simple_test_cases + investigation_test_cases
]

Eval(
    name=project_name,
    data=test_cases,
    task=k8s_agent,
    scores=[OpsmateScorer],
    max_concurrency=1,
)


# create a temp directory and copy all the scenarios files to it
temp_dir = tempfile.mkdtemp()
for file in os.listdir("evals/scenarios"):
    shutil.copy(f"evals/scenarios/{file}", temp_dir)

text_edit_test_cases = [
    {
        "input": f"add resource request and limit to the deploy in {temp_dir}/text-edit-001-missing-resources-config.yaml",
        "expected": "the resource and requests exist in the deployment, the kubernetes config is correct",
        "metadata": {
            "file_path": f"{temp_dir}/text-edit-001-missing-resources-config.yaml",
        },
        "tags": ["k8s", "text-edit"],
    },
    {
        "input": f"remove the liveness probe from the deploy in {temp_dir}/text-edit-002-remove-config.yaml",
        "expected": "the deployment does not have a liveness probe, the kubernetes config is correct",
        "metadata": {
            "file_path": f"{temp_dir}/text-edit-002-remove-config.yaml",
        },
        "tags": ["k8s", "text-edit"],
    },
    {
        "input": f"""Create a nginx-deploy.yml file in the {temp_dir} directory  with:
* a namespace called `demo-ingress`
* a deployment called `nginx-deploy` deployed in the `demo-ingress` namespace
* a service called `nginx-service` deployed in the `demo-ingress` namespace with cluster ip
Please carry out the operations above step by step.
        """,
        "expected": """
* a namespace called `demo-ingress` is created
* a deployment called `nginx-deploy` is deployed in the `demo-ingress` namespace
* a service called `nginx-service` is deployed in the `demo-ingress` namespace that uses the deployment as its selector
""",
        "metadata": {
            "file_path": f"{temp_dir}/nginx-deploy.yml",
        },
        "tags": ["k8s", "text-edit"],
    },
    {
        "input": f"add a new service account called team-a-sa in the team-a namespace in the {temp_dir}/text-edit-003-insert.yaml file",
        "expected": """
* a namespace called `team-a` exists
* a service account called `team-a-sa` exists in the `team-a` namespace
""",
        "metadata": {
            "file_path": f"{temp_dir}/text-edit-003-insert.yaml",
        },
        "tags": ["k8s", "text-edit"],
    },
    {
        "input": f"find the namespace that has the name `eastegg` in the confg files in {temp_dir} directory",
        "expected": "a namespace called `eastegg` exists in the {temp_dir}/text-edit-004-search.yaml file",
        "metadata": {},
        "tags": ["k8s", "text-edit"],
    },
]

text_edit_test_cases = [
    {
        **case,
        "tags": [model, *case["tags"]],
        "metadata": {"model": model, **case["metadata"]},
    }
    for model in models
    for case in text_edit_test_cases
]

Eval(
    name=project_name,
    data=text_edit_test_cases,
    task=k8s_agent,
    scores=[TextEditScorer],
    max_concurrency=1,
)
