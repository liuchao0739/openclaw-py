from __future__ import annotations

from typing import Any


def build_provider_runtime(
    provider: str,
    config: dict[str, Any] | None = None,
    auth: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "provider": provider,
        "config": config or {},
        "auth": auth or {},
        "state": {},
    }


def resolve_provider_runtime(
    provider: str,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return build_provider_runtime(provider, config)
