from braintrust import Eval, EvalHooks
from evals.scorers import OpsmateScorer
from opsmate.contexts import k8s_ctx
from opsmate.dino import run_react
from opsmate.dino.types import ReactAnswer
from opsmate.libs.core.trace import start_trace
from opsmate.config import config
from opsmate.runtime import LocalRuntime
from opentelemetry import trace
import structlog
import os
import tempfile
import shutil
import jinja2
import subprocess

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


def setup_hook(hooks: EvalHooks):
    setups = hooks.metadata.get("setups", [])
    for setup in setups:
        subprocess.run(setup, shell=True)


async def k8s_agent(question: str, hooks: EvalHooks):
    setup_hook(hooks)

    with tracer.start_as_current_span("eval_k8s_agent") as span:
        span.set_attribute("question", question)

        rendered_question = jinja2.Template(question).render(**hooks.metadata)
        span.set_attribute("rendered_question", rendered_question)
        hooks.metadata["input"] = rendered_question

        try:
            runtimes = {
                "ShellCommand": LocalRuntime(),
            }
            for runtime in runtimes.values():
                await runtime.connect()

            contexts = await k8s_ctx.resolve_contexts(runtimes=runtimes)
            tools = k8s_ctx.resolve_tools()
            async for output in run_react(
                rendered_question,
                contexts=contexts,
                tools=tools,
                model=hooks.metadata.get("model"),
                tool_call_context={
                    "runtimes": runtimes,
                },
            ):
                logger.info("output", output=output)

            if isinstance(output, ReactAnswer):
                return output.answer
            else:
                raise ValueError(f"Unexpected output type: {type(output)}")
        finally:
            for runtime in runtimes.values():
                await runtime.disconnect()


# create a temp directory and copy all the scenarios files to it
temp_dir = tempfile.mkdtemp()
for file in os.listdir("evals/scenarios"):
    shutil.copy(f"evals/scenarios/{file}", temp_dir)


simple_test_cases = [
    {
        "input": "how many pods are running in the cluster?",
        "expected": "there are {{pod_num}} pods running in the cluster",
        "tags": ["k8s", "simple"],
        "metadata": {
            "scorer": "CorrectnessScorer",
            "cmds": {
                "pod_num": "kubectl get pods -A --no-headers | wc -l",
            },
        },
    },
    {
        "input": "how many coredns pods are running in the cluster?",
        "expected": "there are {{coredns_num}} coredns pods running in the cluster",
        "tags": ["k8s", "simple"],
        "metadata": {
            "scorer": "CorrectnessScorer",
            "cmds": {
                "coredns_num": "kubectl get pods -A --no-headers | grep -i coredns | wc -l",
            },
        },
    },
    {
        "input": "how many nodes are running in the cluster?",
        "expected": "there are {{node_num}} nodes running in the cluster",
        "tags": ["k8s", "simple"],
        "metadata": {
            "scorer": "CorrectnessScorer",
            "cmds": {
                "node_num": "kubectl get nodes --no-headers | wc -l",
            },
        },
    },
    {
        "input": "list the name of namespaces in the cluster",
        "expected": "the namespaces in the cluster are {{namespaces}}",
        "tags": ["k8s", "simple"],
        "metadata": {
            "scorer": "CorrectnessScorer",
            "cmds": {
                "namespaces": "kubectl get namespaces --no-headers | awk '{print $1}'",
            },
        },
    },
    {
        "input": "what is the version of the kubernetes cluster?",
        "expected": "the version of the kubernetes cluster is {{version}}",
        "tags": ["k8s", "simple"],
        "metadata": {
            "scorer": "CorrectnessScorer",
            "cmds": {
                "version": """kubectl version | grep -i "Server Version" | awk '{print $3}'""",
            },
        },
    },
    {
        "input": "how to start an ephemeral ubuntu 24.04 pod in the cluster with interactive shell, return the command to run",
        "expected": "kubectl run ubuntu --image=ubuntu:24.04 --rm -ti -- bash",
        "tags": ["k8s", "simple"],
        "metadata": {
            "scorer": "CorrectnessScorer",
        },
    },
    {
        "input": "what RBAC permissions does content-manager-sa in the content ns have",
        "expected": "the `content-manager-sa` in the `content-service` namespace has get, list, watch access to pods and services in the `content-service` namespace, granted through the `content-reader` role.",
        "tags": ["k8s", "simple"],
        "metadata": {
            "scorer": "CorrectnessScorer",
        },
    },
]

investigation_test_cases = [
    {
        "input": "what is the issue with the finance-app deployment, please summarise the root cause in 2 sentences.",
        "expected": "the finance-app deployment is experiencing OOM (Out of Memory) kill errors, caused by the stress command from the polinux/stress image.",
        "tags": ["k8s", "investigation"],
        "metadata": {
            "scorer": "CorrectnessScorer",
        },
    },
    {
        "input": "why the ecomm-shop service is not running, please summarise the root cause in 2 sentences.",
        "expected": "the ecomm-shop service is not running due to misconfigured readiness probe.",
        "tags": ["k8s", "investigation"],
        "metadata": {
            "scorer": "CorrectnessScorer",
        },
    },
    {
        "input": "why the accounting software is not deployed, please summarise the root cause in 2 sentences.",
        "expected": "the accounting software is not deployed because it's not schedulable, due it is not tolerated to taint node-role.kubernetes.io/control-plane",
        "tags": ["k8s", "investigation"],
        "metadata": {
            "scorer": "CorrectnessScorer",
        },
    },
    {
        "input": "why the hr-app is not running, please summarise the root cause in 2 sentences.",
        "expected": "the hr-app is not running because the container image `do-not-exist-image:1.0.1` does not exist.",
        "tags": ["k8s", "investigation"],
        "metadata": {
            "scorer": "CorrectnessScorer",
        },
    },
    {
        "input": "why the innovation app is not ready? only investigate do not fix the issue, summarise the root cause in 2 sentences.",
        "expected": "the innovation app is not ready because of database connection issues. The `mysql-service` that is supposed to be used by the app does not exist.",
        "tags": ["k8s", "investigation"],
        "metadata": {
            "scorer": "CorrectnessScorer",
        },
    },
    {
        "input": "why the pod in the default namespace cannot access grafana service, please investigate and summarise the root cause in 2 sentences.",
        "expected": "This is because the network policy `monitoring/grafana` is blocking the access to the grafana service. It is only allows traffic from pods with `app.kubernetes.io/name=prometheus` label within the same `monitoring` namespace.",
        "tags": ["k8s", "investigation"],
        "metadata": {
            "scorer": "CorrectnessScorer",
        },
    },
    {
        "input": "what's wrong with the content-app service? Please investigate and summarize the root cause in 2 sentences.",
        "expected": "The content-manager pod is failing to access ConfigMaps and Secrets due to insufficient RBAC permissions. The service account only has permissions for pods and services, but lacks permissions for ConfigMaps and Secrets resources.",
        "tags": ["k8s", "investigation"],
        "metadata": {
            "scorer": "CorrectnessScorer",
        },
    },
    {
        "input": "The audit server in the audit namespace doesn't appear to be functioning correctly. Please investigate and summarize the root cause in a few sentences.",
        "expected": """
        The audit server is not functioning correctly because it is unable to connect to the MySQL database.
        This is due to the misconfigured matchLabels in the NetworkPolicy `audit/audit-server`.
        The matchLabels are `app: audit-app` instead of `app: audit-server`.
        """,
        "tags": ["k8s", "investigation"],
        "metadata": {
            "scorer": "CorrectnessScorer",
        },
    },
]


def seed_text_edit_scenario(filename: str):
    temp_dir = tempfile.mkdtemp()

    if os.path.exists(f"evals/scenarios/{filename}"):
        shutil.copy(f"evals/scenarios/{filename}", temp_dir)
    return {
        "temp_dir": temp_dir,
        "file_path": f"{temp_dir}/{filename}",
    }


text_edit_test_cases = [
    {
        "input": "add resource request and limit to the deploy in {{file_path}}",
        "expected": "the resource and requests exist in the deployment, the kubernetes config is correct",
        "metadata": {
            "scorer": "TextEditScorer",
            "filename": "text-edit-001-missing-resources-config.yaml",
        },
        "tags": ["k8s", "text-edit"],
    },
    {
        "input": "remove the liveness probe from the deploy in {{file_path}}",
        "expected": "the deployment does not have a liveness probe, the kubernetes config is correct",
        "metadata": {
            "scorer": "TextEditScorer",
            "filename": "text-edit-002-remove-config.yaml",
        },
        "tags": ["k8s", "text-edit"],
    },
    {
        "input": """Create a nginx-deploy.yml file in the {{temp_dir}} directory with:
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
            "scorer": "TextEditScorer",
            "filename": "nginx-deploy.yml",
        },
        "tags": ["k8s", "text-edit"],
    },
    {
        "input": "add a new service account called team-a-sa in the team-a namespace in the {{file_path}} file",
        "expected": """
* a namespace called `team-a` exists
* a service account called `team-a-sa` exists in the `team-a` namespace
""",
        "metadata": {
            "scorer": "TextEditScorer",
            "filename": "text-edit-003-insert.yaml",
        },
        "tags": ["k8s", "text-edit"],
    },
    {
        "input": "find the namespace that has the name `eastegg` in the confg files in {{temp_dir}} directory",
        "expected": "a namespace called `eastegg` exists in the {{file_path}} file",
        "metadata": {
            "scorer": "TextEditScorer",
            "filename": "text-edit-004-search.yaml",
        },
        "tags": ["k8s", "text-edit"],
    },
]

mitigation_test_cases = [
    {
        "input": """create a single pod of image `httpd:2.4.41-alpine` in the namespace `default`.
The pod should be named `pod1` and container should be named `pod1-container`.
""",
        "metadata": {
            "scorer": "MitigationScorer",
            "criteria": """
* the pod is created in the `default` namespace
* the pod uses the image `httpd:2.4.41-alpine`
* the pod is named `pod1`
* the pod uses the container named `pod1-container`
""",
            "cmds": {
                "get_pod": "kubectl get pod pod1 -oyaml",
            },
            "fact": """Here is the output of the pod:
```
{{get_pod}}
```
""",
            "cleanups": [
                "kubectl delete pod pod1",
            ],
        },
        "tags": ["k8s", "mitigation"],
    },
    {
        "input": """Team foo needs to create a kubernetes job. This Job should run image `busybox:1.31.0` and execute `sleep 2 && echo done`.
It should be in namespace `foo`, run a total of 3 times and should execute 2 runs in parallel.

Each pod created by the Job should have the label id: `awesome-job`.
The job should be named `foo-new-job` and the container `foo-new-job-container`.

Please create the kubernetes job and verify the output.""",
        "metadata": {
            "scorer": "MitigationScorer",
            "criteria": """
* the job is created in the `foo` namespace
* the name of the job is `foo-new-job`
* the job has an `id=awesome-job` label
* the job has a parallelism of 2
* the job has a completions of 3
* the job has a container named `foo-new-job-container`
""",
            "cmds": {
                "get_job": "kubectl -n foo get job foo-new-job -oyaml",
            },
            "setups": [
                "kubectl create namespace foo || true",
            ],
            "fact": """Here is the output of the job:
```
{{get_job}}
```
""",
            "cleanups": [
                "kubectl delete job foo-new-job",
                "kubectl delete namespace foo",
            ],
        },
        "tags": ["k8s", "mitigation"],
    },
    {
        "input": """Team bar needs 3 Pods of image httpd:2.4-alpine, create a Deployment named bar-123 for this. The containers should be named bar-pod-123.
Each container should have a memory request of 20Mi and a memory limit of 50Mi.
Team bar has its own ServiceAccount bar-sa-v2 under which the Pods should run. The Deployment should be in Namespace bar.
Please create the kubernetes deployment and verify the output.""",
        "metadata": {
            "scorer": "MitigationScorer",
            "setups": [
                "kubectl create namespace bar || true",
                "kubectl create serviceaccount bar-sa-v2 -n bar",
            ],
            "cleanups": [
                "kubectl delete namespace bar",
            ],
            "criteria": """
* the deployment is created in the `bar` namespace
* the deployment has a service account named `bar-sa-v2`
* the deployment has a container named `bar-pod-123`
* the container has a memory request of 20Mi and a memory limit of 50Mi
* the deployment has 3 replicas
""",
            "cmds": {
                "get_deployment": "kubectl -n bar get deployment bar-123 -oyaml",
            },
            "fact": """Here is the output of the deployment:
```
{{get_deployment}}
```
""",
        },
        "tags": ["k8s", "mitigation"],
    },
    {
        "input": """Team secret-lab has its own ServiceAccount named da-sa in Namespace secret-lab.
A coworker needs the token from the Secret that belongs to that ServiceAccount.
Please provide the base64 decoded token of the Secret to the coworker.
        """,
        "metadata": {
            "scorer": "MitigationScorer",
            "setups": [
                "kubectl create namespace secret-lab || true",
                "kubectl create serviceaccount da-sa -n secret-lab",
                """kubectl apply -f - <<EOF
apiVersion: v1
kind: Secret
type: kubernetes.io/service-account-token
metadata:
  name: da-sa-secret
  namespace: secret-lab
  annotations:
    kubernetes.io/service-account.name: da-sa
EOF
""",
            ],
            "cleanups": [
                "kubectl delete namespace secret-lab",
            ],
            "cmds": {
                "get_secret": "kubectl -n secret-lab get secret da-sa-secret -o jsonpath='{.data.token}' | base64 -d",
            },
            "criteria": """
* output from opsmate for the service account token is correct
""",
            "fact": """Here is the output of the secret:
```
{{get_secret}}
```

Here is the output from opsmate:
```
{{output}}
```
""",
        },
        "tags": ["k8s", "mitigation"],
    },
    {
        "input": """Create a single Pod named pod6 in Namespace default of image busybox:1.31.0.
    The Pod should have a readiness-probe executing cat /tmp/ready.
    This will set the container ready only if the file /tmp/ready exists.

    The Pod should run the command touch `/tmp/ready && sleep 1d`, which will create the necessary file to be ready and then idles.
    Create the Pod and confirm it starts.
""",
        "metadata": {
            "scorer": "MitigationScorer",
            "cmds": {
                "get_pod": "kubectl get pod pod6 -oyaml",
            },
            "fact": """Here is the output of the pod:
```
{{get_pod}}
```
""",
            "cleanups": [
                "kubectl delete pod pod6",
            ],
            "criteria": """
* the pod6 is created in the `default` namespace
* the pod6 has a readiness-probe executing `cat /tmp/ready`
* the pod6 should have "sleep 1d" as either command or args
""",
        },
        "tags": ["k8s", "mitigation"],
    },
    {
        "input": """Team alpha decided to take over control of one e-commerce webserver from Team beta.
The e-commerce system is called `my-happy-socks` in the `alpha` namespace.
Search for the correct deploy in Namespace alpha and move it to Namespace beta, and remove the deployment from alpha.

Please move the kubernetes deployment and verify the output.
""",
        "metadata": {
            "scorer": "MitigationScorer",
            "setups": [
                "kubectl create namespace alpha || true",
                "kubectl create namespace beta || true",
                """kubectl apply -f - <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
    namespace: alpha
    name: my-happy-socks
    labels:
        app: my-happy-socks
spec:
    replicas: 1
    selector:
        matchLabels:
            app: my-happy-socks
    template:
        metadata:
            labels:
                app: my-happy-socks
        spec:
            containers:
            - name: container
              image: nginx:1.27.4-alpine-slim
EOF
""",
            ],
            "cleanups": [
                "kubectl delete namespace alpha",
                "kubectl delete namespace beta",
            ],
            "criteria": """
    * the deployment is created like for like in the `beta` namespace
    * the deployment is removed from the `alpha` namespace
    """,
            "cmds": {
                "get_deploy": "kubectl get deploy -n beta my-happy-socks -oyaml",
                "get_deploy_alpha": "kubectl get deploy -n alpha",
            },
            "fact": """This is the previous deployment in alpha namespace:
```
apiVersion: apps/v1
kind: Deployment
metadata:
    namespace: alpha
    name: my-happy-socks
    labels:
        app: my-happy-socks
spec:
    replicas: 1
    selector:
        matchLabels:
            app: my-happy-socks
    template:
        metadata:
            labels:
                app: my-happy-socks
        spec:
            containers:
            - name: container
              image: nginx:1.27.4-alpine-slim
```

Here is the output of the beta deployment:
```
{{get_deploy}}
```

Here is the current deployment resources in alpha namespace:
```
{{get_deploy_alpha}}
```
""",
        },
        "tags": ["k8s", "mitigation"],
    },
]

models = ["claude-3-7-sonnet-20250219", "gpt-4o"]

test_cases = [
    {
        **case,
        "tags": [model, *case["tags"]],
        "metadata": {
            "model": model,
            **case["metadata"],
            **(
                seed_text_edit_scenario(case["metadata"]["filename"])
                if "filename" in case["metadata"]
                else {}
            ),
        },
    }
    for model in models
    for case in simple_test_cases
    + investigation_test_cases
    + text_edit_test_cases
    + mitigation_test_cases
]

Eval(
    name=project_name,
    data=test_cases,
    task=k8s_agent,
    scores=[OpsmateScorer],
    max_concurrency=1,
)
