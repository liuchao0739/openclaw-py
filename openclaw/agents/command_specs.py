from __future__ import annotations

from typing import Any


def build_command_spec(
    name: str,
    handler: Any = None,
    description: str = "",
    **metadata: Any,
) -> dict[str, Any]:
    return {
        "name": name,
        "handler": handler,
        "description": description,
        "metadata": metadata,
    }


def register_command_group(
    group_name: str,
    commands: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "group": group_name,
        "commands": commands or [],
    }
