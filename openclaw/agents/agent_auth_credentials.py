from __future__ import annotations

from typing import Any


def resolve_auth_credentials(
    provider: str,
    config: dict[str, Any] | None = None,
    env: dict[str, str] | None = None,
) -> dict[str, Any] | None:
    config = config or {}
    env = env or {}

    cred_key = f"{provider.upper()}_API_KEY"
    api_key = env.get(cred_key) or config.get("apiKey")
    if not api_key:
        return None

    return {
        "provider": provider,
        "apiKey": api_key,
        "source": "env" if env.get(cred_key) else "config",
    }


def discover_auth_providers(
    config: dict[str, Any] | None = None,
    env: dict[str, str] | None = None,
) -> list[str]:
    config = config or {}
    env = env or {}
    providers: set[str] = set()

    for key in env:
        if key.endswith("_API_KEY"):
            providers.add(key.replace("_API_KEY", "").lower())

    for provider in config.get("providers", {}):
        providers.add(provider)

    return sorted(providers)
