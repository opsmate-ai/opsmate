from pydantic import BaseModel, Field, field_validator
import yaml


class Category(BaseModel):
    name: str = Field(description="The name of the category")
    description: str = Field(description="The description of the category")


node_issues = Category(
    name="Node Issues",
    description="""
* Resource Exhaustion: Check for CPU, memory, or disk pressure on nodes.
* Node Connectivity: Verify network connectivity between nodes and troubleshoot any network issues.
* Node Status: Look for nodes that may be in NotReady or Unknown states due to issues with kubelet, systemd, or OS configuration.
* Log Analysis: Inspect system logs (e.g., kubelet, Docker/container runtime logs).
    """,
)

pod_and_container_issues = Category(
    name="Pod and Container Issues",
    description="""
* Pod Lifecycle: Examine Pod status, including Pending, CrashLoopBackOff, or Evicted.
* Container Logs: Use kubectl logs to access container logs for debugging.
* Container Image Issues: Ensure containers can pull images correctly; look for authorization or registry issues.
* Pod Resource Limits: Verify resource requests and limits to avoid resource starvation or throttling.
* Readiness/Liveness Probes: Check if probes are misconfigured, causing Pod restarts or failures.
    """,
)

network_issues = Category(
    name="Network Issues",
    description="""
* Service Discovery: Ensure services are discoverable and accessible by checking DNS and kube-proxy configurations.
* Network Policies: Review network policies that may be restricting traffic between Pods or namespaces.
* Ingress/Egress Issues: Inspect Ingress controllers and verify firewall or security group settings for network traffic.
* Service and Endpoint Issues: Verify that Services have corresponding Endpoints and that they point to healthy Pods.
    """,
)


class Step(BaseModel):
    command: str = Field(description="The command to run")
    expected_output: str | None = Field(
        description="The expected output of the command", default=None
    )
    exit_code: int | None = Field(
        description="The expected exit code of the command", default=None
    )


class VerificationStep(Step):
    pass


class K8SStep(BaseModel):
    description: str = Field(description="The description of the step")
    manifest: str = Field(description="The kubernetes manifest to apply")

    @field_validator("manifest")
    def validate_manifest(cls, v):
        try:
            yaml.safe_load(v)
        except Exception as e:
            raise ValueError("Invalid manifest") from e
        return v


class TroubleshootingQuestion(BaseModel):
    """
    Troubleshooting question for SRE candidates
    """

    namespace: str = Field(
        description="The namespace to be created for the troubleshooting question",
    )

    steps_to_create_issue: list[K8SStep] = Field(
        description="A list of steps to create the issue"
    )
    question: str = Field(description="Question to ask the candidate")

    issue_produced_verification: list[VerificationStep] = Field(
        description="Commands to verify the issue has been created"
    )
    fix_verification: list[VerificationStep] = Field(
        description="Commands to verify the issue has been fixed"
    )
    root_cause: str = Field(description="The root cause of the issue")


class QNA(BaseModel):
    description: str = Field(description="The description of the question")
    question: str = Field(description="The question to ask the candidate")
    answer_command: str | None = Field(
        description="The command to verify the answer", default=None
    )
    answer_verification: list[VerificationStep] = Field(
        description="Commands to verify the answer",
        default=[],
    )
    steps_to_create_issue: list[K8SStep] = Field(
        description="A list of steps to create the issue", default=[]
    )
    similarity_threshold: float = Field(
        description="The similarity threshold to use for the question",
        ge=0.0,
        le=1.0,
        default=0.6,
    )
    namespace: str | None = Field(
        description="The namespace to be created for the question",
        default=None,
    )
    cleanup_steps: list[Step] = Field(
        description="Steps to clean up the issue", default=[]
    )
