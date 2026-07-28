from __future__ import annotations

from typing import Any


def build_cli_runner_config(
    config: dict[str, Any] | None = None,
    options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "config": config or {},
        "options": options or {},
    }


def run_cli_command(
    command: str,
    args: list[str] | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "command": command,
        "args": args or [],
        "config": config or {},
        "status": "pending",
    }
