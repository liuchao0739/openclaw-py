from __future__ import annotations

from typing import Any


def has_agent_copy_override(credential: dict[str, Any]) -> bool | None:
    override = credential.get("agentCopyOverride")
    if override is None:
        return None
    return bool(override)


def has_copyable_oauth_material(credential: dict[str, Any]) -> bool:
    if credential.get("type") != "oauth":
        return True
    if credential.get("refreshToken"):
        return True
    if credential.get("refreshTokenRef"):
        return True
    return False
