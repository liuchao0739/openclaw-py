from __future__ import annotations

from typing import Any

from openclaw.plugin_sdk.provider_auth import read_claude_cli_credentials_cached

from .cli_constants import CLAUDE_CLI_BACKEND_ID

_provider_id = CLAUDE_CLI_BACKEND_ID


def _resolve_claude_cli_synthetic_auth() -> dict[str, Any] | None:
    credential = read_claude_cli_credentials_cached(allowKeychainPrompt=False)
    if not credential:
        return None
    if credential.get("type") == "oauth":
        return {
            "apiKey": credential.get("access"),
            "source": "Claude CLI native auth",
            "mode": "oauth",
            "expiresAt": credential.get("expires"),
        }
    return {
        "apiKey": credential.get("token"),
        "source": "Claude CLI native auth",
        "mode": "token",
        "expiresAt": credential.get("expires"),
    }


anthropic_provider_discovery: dict[str, Any] = {
    "id": _provider_id,
    "label": "Claude CLI",
    "docsPath": "/providers/models",
    "auth": [],
    "resolveSyntheticAuth": lambda params: (
        _resolve_claude_cli_synthetic_auth()
        if params.get("provider") == _provider_id
        else None
    ),
}