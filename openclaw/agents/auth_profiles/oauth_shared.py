from __future__ import annotations

from typing import Any


def build_oauth_shared_config(
    provider: str,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    config = config or {}
    return {
        "provider": provider,
        "clientId": config.get("clientId"),
        "clientSecret": config.get("clientSecret"),
        "redirectUri": config.get("redirectUri", "http://localhost:3000/oauth/callback"),
        "scopes": config.get("scopes", []),
    }
