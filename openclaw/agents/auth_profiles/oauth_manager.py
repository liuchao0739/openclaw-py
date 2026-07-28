from __future__ import annotations

from typing import Any


def create_oauth_manager(
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "config": config or {},
        "sessions": {},
        "state": "idle",
    }


def start_oauth_flow(
    manager: dict[str, Any],
    provider: str,
    scopes: list[str] | None = None,
) -> dict[str, Any]:
    manager["state"] = "flowing"
    return {
        "provider": provider,
        "scopes": scopes or [],
        "status": "started",
    }
