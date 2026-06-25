"""Test-only config helpers for gateway status SecretRef scenarios."""

from __future__ import annotations

from typing import Any, Literal


def create_secret_ref_gateway_config(
    gateway_mode: Literal["local", "remote"] | None = None,
) -> dict[str, Any]:
    """Build gateway config where local and remote auth values use environment SecretRefs."""
    config: dict[str, Any] = {
        "secrets": {
            "defaults": {
                "env": "default",
            },
        },
        "gateway": {
            "auth": {
                "mode": "token",
                "token": {"source": "env", "provider": "default", "id": "OPENCLAW_GATEWAY_TOKEN"},
                "password": {"source": "env", "provider": "default", "id": "OPENCLAW_GATEWAY_PASSWORD"},
            },
            "remote": {
                "url": "wss://remote.example:18789",
                "token": {"source": "env", "provider": "default", "id": "REMOTE_GATEWAY_TOKEN"},
                "password": {"source": "env", "provider": "default", "id": "REMOTE_GATEWAY_PASSWORD"},
            },
        },
    }
    if gateway_mode:
        config["gateway"]["mode"] = gateway_mode
    return config
