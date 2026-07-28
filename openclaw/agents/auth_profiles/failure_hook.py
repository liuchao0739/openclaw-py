from __future__ import annotations

from typing import Any


def mark_auth_profile_failure(
    store: dict[str, Any],
    profile_id: str,
    reason: str,
) -> None:
    usage_stats = store.setdefault("usageStats", {}).setdefault(profile_id, {})
    usage_stats["errorCount"] = usage_stats.get("errorCount", 0) + 1
    usage_stats["lastFailureAt"] = __import__("time").time() * 1000
    usage_stats["cooldownReason"] = reason


def clear_auth_profile_failure(
    store: dict[str, Any],
    profile_id: str,
) -> None:
    if profile_id in store.get("usageStats", {}):
        del store["usageStats"][profile_id]
