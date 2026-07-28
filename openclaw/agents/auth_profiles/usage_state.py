from __future__ import annotations

from typing import Any


def build_usage_state(
    store: dict[str, Any] | None = None,
) -> dict[str, Any]:
    store = store or {}
    return {
        "usageStats": store.get("usageStats", {}),
        "order": store.get("order", {}),
    }


def resolve_usage_state(
    store: dict[str, Any],
    profile_id: str,
) -> dict[str, Any]:
    return store.get("usageStats", {}).get(profile_id, {})
