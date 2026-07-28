from __future__ import annotations

from typing import Any


def resolve_auth_profile_order(
    store: dict[str, Any],
    provider: str,
) -> list[str]:
    order = store.get("order", {}).get(provider, [])
    if isinstance(order, list):
        return order
    return []


def reorder_auth_profiles(
    store: dict[str, Any],
    provider: str,
    profile_ids: list[str],
) -> dict[str, Any]:
    store.setdefault("order", {})[provider] = profile_ids
    return store
