"""Configured binding built-in registration."""

from __future__ import annotations

from typing import Any


_CONFIGURED_BINDING_CONSUMERS: list[Any] = []


def register_configured_binding_consumer(consumer: Any) -> None:
    """Register a configured binding consumer."""
    if consumer not in _CONFIGURED_BINDING_CONSUMERS:
        _CONFIGURED_BINDING_CONSUMERS.append(consumer)


def ensure_configured_binding_builtins_registered() -> None:
    """Register configured binding consumers bundled with core."""
    try:
        from openclaw.channels.plugins.acp_configured_binding_consumer import (
            acp_configured_binding_consumer,
        )

        register_configured_binding_consumer(acp_configured_binding_consumer)
    except Exception:
        pass


def get_configured_binding_consumers() -> list[Any]:
    """Get all registered configured binding consumers."""
    return list(_CONFIGURED_BINDING_CONSUMERS)
