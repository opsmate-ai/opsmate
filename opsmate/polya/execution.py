import instructor
from anthropic import Anthropic
from openai import AsyncOpenAI
from pydantic import BaseModel, Field
from typing import List, Union
import subprocess
from jinja2 import Template
from opsmate.polya.models import TaskPlan
from opsmate.polya.planning import planning
from opsmate.polya.understanding import (
    generate_report,
    initial_understanding,
    info_gathering,
)
import asyncio


async def execute(task_plan: TaskPlan):
    task_map = {}
    for task in task_plan.subtasks:
        task_map[task.id] = task

    all_task_results = {}

    for task in task_plan.subtasks:
        task_results = []
        for subtask in task.subtasks:
            task_result = all_task_results.get(subtask.id, None)
            if task_result is not None:
                task_results.append(task_result)

        task_result = await task.execute(task_map, task_results)
        all_task_results[task.id] = task_result

    return all_task_results


async def main():
    context = """
# Summary
The `payment-service` deployment in the `payment` namespace is facing issues with successfully rolling out the new pods. Despite a rolling update strategy allowing for some pods to be unavailable during updates, the deployment is failing to meet the progress deadline, resulting in an overall unsuccessful rollout.

# Findings
1. **Deployment Status:**
   - The deployment desires 2 replicas but currently has 3, indicating an excess pod count beyond the specification.
   - 2 replicas are available while 1 remains unavailable, even though the system considers the "Available" condition "True."
   - Progress status of the deployment is marked as "False" due to "ProgressDeadlineExceeded."

2. **Probe Failures:**
   - The readiness probe for the pod `payment-service-d4b67d787-pr8zr` has failed, returning a 404 HTTP status code, indicating that the health check endpoint may be incorrect or the service endpoint may be down.
   - Back-off restarts have been triggered due to container failures.

3. **Recent Changes:**
   - No changes in revision causes within the rollout history for revisions 2 and 3. This suggests that failures are not due to recent deployment changes but rather existing misconfigurations or dependencies.

4. **Kubernetes Events:**
   - Other events echo the same issues: back-off restart and readiness probe failure, highlighting a recurring problem in the service health checks.

# Recommendation
- **Verify Health Check Endpoints:** Ensure the readiness probe and liveness probe endpoints are correct, and confirm that the service they monitor is operational.
- **Resource Configurations:** Check resource allocations such as CPU and memory for adequacy as resource constraints might lead to readiness probe failures.
- **Debug Container Logs:** Review the container logs of the failing pod `payment-service-d4b67d787-pr8zr` to get more insight into why the readiness checks return 404 errors.
- **Check Dependencies:** Investigate any upstream dependencies that may be affecting the pod's ability to become "Ready."

# Out of scope
- The deployment previously did not show issues with availability conditions, suggesting that the core deployment strategy is sound but other environmental factors or configuration errors are at play.
- No new features or massive changes recorded, reducing the likelihood that new code is the cause of these problems.
"""
    task_plan = await planning(context=context, instruction="how can this be resolved?")

    print(task_plan.model_dump_json(indent=2))


if __name__ == "__main__":
    asyncio.run(main())
