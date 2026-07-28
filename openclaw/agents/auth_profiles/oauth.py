from __future__ import annotations

from typing import Any


def build_oauth_config(
    provider: str,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    config = config or {}
    return {
        "provider": provider,
        "clientId": config.get("clientId"),
        "clientSecret": config.get("clientSecret"),
        "redirectUri": config.get("redirectUri"),
        "scopes": config.get("scopes", []),
    }


def exchange_oauth_token(
    provider: str,
    code: str,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "provider": provider,
        "accessToken": None,
        "refreshToken": None,
        "expiresIn": 0,
    }
