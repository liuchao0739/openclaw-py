from __future__ import annotations

from typing import Any


def build_embedded_agent_helpers(
    config: dict[str, Any] | None = None,
    env: dict[str, str] | None = None,
) -> dict[str, Any]:
    return {
        "config": config or {},
        "env": env or {},
        "providers": {},
    }


def resolve_embedded_provider_id(
    provider: str,
    helpers: dict[str, Any] | None = None,
) -> str | None:
    helpers = helpers or {}
    providers = helpers.get("providers", {})
    if provider in providers:
        return provider
    return None
