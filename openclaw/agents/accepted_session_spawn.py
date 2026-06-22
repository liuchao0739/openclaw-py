"""Accepted session spawn helpers."""

from __future__ import annotations


def has_accepted_session_spawn(accepted_session_spawns: list[object] | None = None) -> bool:
    if not accepted_session_spawns:
        return False
    return len(accepted_session_spawns) > 0