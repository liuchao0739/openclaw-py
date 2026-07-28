from __future__ import annotations

from typing import Any


def repair_auth_profile_store(
    store: dict[str, Any],
) -> dict[str, Any]:
    store = dict(store)
    profiles = dict(store.get("profiles", {}))
    repaired_profiles: dict[str, Any] = {}
    removed: list[str] = []

    for profile_id, credential in profiles.items():
        if not isinstance(credential, dict):
            removed.append(profile_id)
            continue
        repaired_profiles[profile_id] = credential

    store["profiles"] = repaired_profiles

    order = store.get("order", {})
    repaired_order: dict[str, Any] = {}
    for provider, profile_ids in order.items():
        if not isinstance(profile_ids, list):
            continue
        valid_ids = [pid for pid in profile_ids if pid in repaired_profiles]
        if valid_ids:
            repaired_order[provider] = valid_ids
    store["order"] = repaired_order

    usage_stats = store.get("usageStats", {})
    repaired_stats: dict[str, Any] = {}
    for pid, stats in usage_stats.items():
        if pid in repaired_profiles:
            repaired_stats[pid] = stats
    store["usageStats"] = repaired_stats

    return store
