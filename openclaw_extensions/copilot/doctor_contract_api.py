"""Doctor contract hooks for the copilot extension config migrations and session-route ownership."""

from __future__ import annotations

from typing import Any

legacy_config_rules: list[dict[str, Any]] = []


def normalize_compatibility_config(params: dict[str, Any]) -> dict[str, Any]:
    """Return config unchanged when no copilot legacy migrations apply."""
    cfg = params["cfg"]
    return {"config": cfg, "changes": []}


session_route_state_owners: list[dict[str, Any]] = [
    {
        "id": "copilot",
        "label": "GitHub Copilot agent runtime",
        "providerIds": ["github-copilot"],
        "runtimeIds": ["copilot"],
        "cliSessionKeys": ["copilot"],
        "authProfilePrefixes": ["github-copilot:"],
    }
]
