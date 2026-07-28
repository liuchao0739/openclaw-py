from __future__ import annotations

from typing import Any


def build_runtime(
    config: dict[str, Any] | None = None,
    plugins: list[Any] | None = None,
) -> dict[str, Any]:
    return {
        "config": config or {},
        "plugins": plugins or [],
        "state": {},
        "initialized": False,
    }


def initialize_runtime(
    runtime: dict[str, Any],
) -> dict[str, Any]:
    runtime["initialized"] = True
    return runtime


def shutdown_runtime(
    runtime: dict[str, Any],
) -> dict[str, Any]:
    runtime["initialized"] = False
    return runtime
