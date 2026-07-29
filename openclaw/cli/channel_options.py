from __future__ import annotations

from typing import Any


def resolve_channel_options(raw: dict | None = None) -> dict:
    if not raw:
        return {}
    options: dict[str, Any] = {}
    for key, value in raw.items():
        if value is not None:
            options[key] = value
    return options


def merge_channel_options(primary: dict, fallback: dict | None = None) -> dict:
    merged = dict(fallback or {})
    merged.update(primary)
    return merged
