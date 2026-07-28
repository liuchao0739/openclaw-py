from __future__ import annotations

from typing import Any


def build_loop(
    max_iterations: int = 50,
    timeout_ms: int = 300000,
) -> dict[str, Any]:
    return {
        "maxIterations": max_iterations,
        "timeoutMs": timeout_ms,
        "iteration": 0,
        "status": "idle",
    }


def step_loop(
    loop: dict[str, Any],
) -> dict[str, Any]:
    loop["iteration"] = loop.get("iteration", 0) + 1
    loop["status"] = "running"
    return loop
