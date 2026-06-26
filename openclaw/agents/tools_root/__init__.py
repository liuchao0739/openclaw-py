"""Agents tools package — session status runtime."""

from __future__ import annotations

from typing import Any


def build_status_text(*args: Any, **kwargs: Any) -> str:
    """Build status text (delegates to status subsystem)."""
    from openclaw.status import resolve_active_fallback_state

    # Minimal stub — full implementation delegates to status/status_text.py
    return "status: ok"
