from __future__ import annotations

from typing import Any


def resolve_external_auth(
    provider: str,
    config: dict[str, Any] | None = None,
    env: dict[str, str] | None = None,
) -> dict[str, Any] | None:
    config = config or {}
    env = env or {}

    key = env.get(f"{provider.upper()}_API_KEY")
    if not key:
        return None

    return {
        "provider": provider,
        "type": "api_key",
        "key": key,
        "source": "environment",
    }
