"""Resolves human-readable labels for paired channel identities.

Mirrors src/pairing/pairing-labels.ts. Self-contained with adapter lookup stub.
"""

from __future__ import annotations

from typing import Any

# Channel-specific id label overrides. Defaults to "userId".
_PAIRING_ADAPTERS: dict[str, dict[str, Any]] = {
    "telegram": {"idLabel": "Telegram user id"},
    "discord": {"idLabel": "Discord user id"},
    "slack": {"idLabel": "Slack user id"},
}


def get_pairing_adapter(channel: str) -> dict[str, Any] | None:
    """Get the pairing adapter for a channel. Stub implementation."""
    return _PAIRING_ADAPTERS.get(channel)


def resolve_pairing_id_label(channel: str) -> str:
    """Resolve the id label for a pairing channel.

    Channel adapters can customize the id label shown in owner approval prompts;
    legacy channels fall back to "userId".
    """
    adapter = get_pairing_adapter(channel)
    if adapter and "idLabel" in adapter:
        return adapter["idLabel"]
    return "userId"
