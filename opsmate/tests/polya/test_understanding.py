from opsmate.polya.understanding import (
    report_breakdown,
    initial_understanding,
    load_inital_understanding,
)
from opsmate.polya.models import Report
import pytest


@pytest.mark.asyncio
async def test_initial_understanding():
    response = await initial_understanding(
        "The 'payment-service' deployment in the 'payment' namespace is unable to successfully rollout?",
    )

    assert response.questions is not None
    assert response.summary is not None


@pytest.mark.asyncio
async def test_load_inital_understanding():
    response = await load_inital_understanding(
        """
# Summary

The 'payment-service' deployment in the 'payment' namespace is unable to successfully rollout

# Questions

- What is the root cause of the issue?
- What are the potential solutions?
- What are the out of scope issues?
"""
    )
    assert response is not None
    assert response.summary is not None
    assert response.questions is not None
    assert len(response.questions) == 3


@pytest.mark.asyncio
async def test_report_breakdown():
    report = Report(
        content="""
## Summary
The 'payment-service' deployment in the 'payment' namespace is unable to successfully rollout. This failure is primarily due to a 'ProgressDeadlineExceeded' status. The deployment issue includes at least one pod with an unhealthy status, stemming from a failed readiness probe that returns an HTTP 404 error. Moreover, the system is experiencing back-off behaviour as it repeatedly attempts to restart a failed container.

## Findings
- **ProgressDeadlineExceeded Status**: This status indicates that the deployment did not progress as expected within the deadline set for rollout.
- **Readiness Probe Failure**: The pod readiness probe is failing, resulting in an HTTP 404 status. This frequently happens when the service within the pod is not running or responding to the readiness probe as configured.
- **Back-Off Event**: The Kubernetes system is in a cycle of trying to restart a failed container, which suggests that there is a persistent failure preventing the container from reaching a running and stable state.
- **Lack of Resource Quotas**: There are no resource limits or quotas defined for the 'payment' namespace, ruling out resource scarcity as the cause of the deployment issue.
- **Undocumented Configuration Changes**: The absence of documented reasons or 'CHANGE-CAUSE' labels in the rollout history of the deployment makes it challenging to pinpoint recent configuration changes as a cause for the issue.

## Potential Solutions
1. **Check and Update Readiness Probe Configuration (50%)**: The readiness probe might be misconfigured or targeting a non-existent endpoint. Ensuring that the endpoint exists and is accurate can resolve the issue.
   - Probability of Success: 50%

2. **Inspect and Amend Container Setup (30%)**: Validate that the container's start command, environment, and other configuration settings are correct, enabling the application to start and run without errors.
   - Probability of Success: 30%

3. **Review Recent Changes (20%)**: Given the lack of documented changes, manually review recent commits or configurations to identify potential errors or missing settings that might be affecting the rollout.
   - Probability of Success: 20%

## Out of Scope
- **Resource Quota Issues**: Since there are no resource constraints in the 'payment' namespace, this is not related to the current problem.
- **Network or Infrastructure Issues**: The findings do not indicate network or broader infrastructure problems affecting the deployment.
"""
    )
    report_extracted = await report_breakdown(report)

    assert len(report_extracted.potential_solutions) == 3

    assert report_extracted.potential_solutions[0].probability == 50
    assert report_extracted.potential_solutions[1].probability == 30
    assert report_extracted.potential_solutions[2].probability == 20

    print(report_extracted.model_dump_json(indent=2))
