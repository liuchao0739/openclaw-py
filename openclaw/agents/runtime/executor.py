from __future__ import annotations

from typing import Any


def build_agent_runtime(
    config: dict[str, Any] | None = None,
    tools: list[Any] | None = None,
    hooks: list[Any] | None = None,
) -> dict[str, Any]:
    return {
        "config": config or {},
        "tools": tools or [],
        "hooks": hooks or [],
        "state": {},
    }


def run_agent_runtime_step(
    runtime: dict[str, Any],
    input_data: dict[str, Any],
) -> dict[str, Any]:
    return {
        "status": "success",
        "output": {},
    }
