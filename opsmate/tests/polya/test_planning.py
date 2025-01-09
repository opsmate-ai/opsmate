import pytest

from opsmate.polya.planning import planning
from opsmate.polya.models import Task, TaskPlan, Solution, ReportExtracted


def test_topological_sort():
    subtasks = [
        Task(
            id=4,
            task="Restart the payment-service deployment to apply the changes.",
            subtasks=[3],
        ),
        Task(
            id=5,
            task="Monitor the payment-service pods to ensure readiness probe success and stable rollout.",
            subtasks=[4],
        ),
        Task(
            id=3,
            task="Update the readiness probe configuration with the correct endpoint.",
            subtasks=[1, 2],
        ),
        Task(
            id=1,
            task="Verify the current readiness probe configuration for the payment-service deployment.",
            subtasks=[],
        ),
        Task(
            id=2,
            task="Identify the correct health check endpoint for the payment-service application.",
            subtasks=[],
        ),
    ]
    task_plan = TaskPlan(
        goal="Fix the deployment payment-service in the payment namespace",
        subtasks=subtasks,
    )

    sorted = task_plan.topological_sort()

    sorted_ids = [task.id for task in sorted]
    assert sorted_ids == [1, 2, 3, 4, 5]


@pytest.mark.asyncio
async def test_planning():
    report_extracted = ReportExtracted(
        summary="The 'payment-service' deployment in the 'payment' namespace is facing rollout issues due to 'ProgressDeadlineExceeded' status, unhealthy pod statuses from failed readiness probes returning HTTP 404 errors, and back-off behavior from repeatedly restarting a failed container.",
        potential_solutions=[
            Solution(
                findings=["ProgressDeadlineExceeded Status", "Readiness Probe Failure"],
                solution="Check and update the readiness probe configuration to ensure it's targeting an existent and correct endpoint.",
                probability=50,
            ),
            Solution(
                findings=["Back-Off Event"],
                solution="Inspect and amend the container setup, verifying commands and environment configurations as correct to enable stable application start-up.",
                probability=30,
            ),
            Solution(
                findings=["Undocumented Configuration Changes"],
                solution="Manually review recent commits or configuration changes to identify any hidden issues or missing settings impacting the rollout.",
                probability=20,
            ),
        ],
    )

    plan = await planning(
        summary=report_extracted.potential_solutions[0].summarize(
            report_extracted.summary
        ),
        facts=[],
        instruction="can you solve the problem based on the context?",
    )

    assert plan.goal is not None
    assert len(plan.subtasks) > 0
