"""Sender display-label helpers shared by channel ingress and audit surfaces."""

from __future__ import annotations

from typing import Any


def resolve_sender_label(
    name: str | None = None,
    username: str | None = None,
    tag: str | None = None,
    e164: str | None = None,
    id: str | None = None,
) -> str | None:
    """Resolve the best one-line sender label from available identity fields."""
    def _norm(v: str | None) -> str | None:
        return v.strip() if v and isinstance(v, str) and v.strip() else None

    n = _norm(name)
    u = _norm(username)
    t = _norm(tag)
    e = _norm(e164)
    i = _norm(id)

    display = n or u or t or ""
    id_part = e or i or ""

    if display and id_part and display != id_part:
        return f"{display} ({id_part})"
    return display or id_part or None
