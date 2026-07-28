from __future__ import annotations

from typing import Any


def resolve_identity(
    config: dict[str, Any] | None = None,
    env: dict[str, str] | None = None,
) -> dict[str, Any]:
    config = config or {}
    return {
        "name": config.get("name", "OpenClaw Agent"),
        "avatar": config.get("avatar"),
        "email": config.get("email"),
        "role": config.get("role", "assistant"),
        "metadata": config.get("metadata", {}),
    }


def build_identity_display_name(identity: dict[str, Any]) -> str:
    name = identity.get("name", "OpenClaw Agent")
    return name
