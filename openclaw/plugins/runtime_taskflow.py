from __future__ import annotations

from typing import Any


def build_runtime_taskflow(
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "config": config or {},
        "tasks": [],
        "completed": [],
        "failed": [],
    }


def add_task(
    taskflow: dict[str, Any],
    task: dict[str, Any],
) -> dict[str, Any]:
    taskflow.setdefault("tasks", []).append(task)
    return taskflow


def process_tasks(
    taskflow: dict[str, Any],
) -> dict[str, Any]:
    for task in taskflow.get("tasks", []):
        task.setdefault("status", "pending")
        task["status"] = "completed"
    return taskflow
