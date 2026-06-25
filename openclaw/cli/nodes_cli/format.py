"""Formatting helpers for node list/pairing CLI output."""

from __future__ import annotations

from typing import Any


def format_permissions(raw: Any) -> str | None:
    """Format node permission maps as a stable ``[permission=yes|no]`` label."""
    if not raw or not isinstance(raw, dict):
        return None

    entries = sorted(
        [(key, value is True) for key, value in raw.items() if key and isinstance(key, str)],
        key=lambda x: x[0],
    )

    if not entries:
        return None

    parts = [f"{key}={'yes' if granted else 'no'}" for key, granted in entries]
    return f"[{', '.join(parts)}]"


def parse_node_list(raw: Any) -> list[dict[str, Any]]:
    """Parse a raw node list response into structured entries.

    Deferred to shared/node-list-parse module; returns empty list when unavailable.
    """
    if isinstance(raw, list):
        return [item for item in raw if isinstance(item, dict)]
    if isinstance(raw, dict) and isinstance(raw.get("nodes"), list):
        return [item for item in raw["nodes"] if isinstance(item, dict)]
    return []


def parse_pairing_list(raw: Any) -> list[dict[str, Any]]:
    """Parse a raw pairing list response into structured entries."""
    if isinstance(raw, list):
        return [item for item in raw if isinstance(item, dict)]
    if isinstance(raw, dict) and isinstance(raw.get("pairings"), list):
        return [item for item in raw["pairings"] if isinstance(item, dict)]
    return []
