import pytest

from opsmate.polya.planning import TaskPlan, planning, Task


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
