from __future__ import annotations

from typing import Any

from openclaw.agents.auth_profiles.types import (
    AuthProfileBlockedSource,
    AuthProfileFailureReason,
    AuthProfileStore,
    ProfileUsageStats,
)


FAILURE_REASON_PRIORITY: list[str] = [
    "auth_permanent",
    "auth",
    "billing",
    "format",
    "model_not_found",
    "overloaded",
    "timeout",
    "rate_limit",
    "empty_response",
    "no_error_details",
    "unclassified",
    "unknown",
]

FAILURE_REASON_SET: set[str] = set(FAILURE_REASON_PRIORITY)

FAILURE_REASON_ORDER: dict[str, int] = {
    reason: idx for idx, reason in enumerate(FAILURE_REASON_PRIORITY)
}


WHAM_USAGE_URL = "https://chatgpt.com/backend-api/wham/usage"
WHAM_TIMEOUT_MS = 3000
WHAM_BURST_COOLDOWN_MS = 15000
WHAM_PROBE_FAILURE_COOLDOWN_MS = 30000
WHAM_HTTP_ERROR_COOLDOWN_MS = 5 * 60 * 1000
WHAM_TOKEN_EXPIRED_COOLDOWN_MS = 12 * 60 * 60 * 1000
WHAM_DEAD_ACCOUNT_COOLDOWN_MS = 24 * 60 * 60 * 1000


def calculate_auth_profile_cooldown_ms(error_count: int) -> int:
    normalized = max(1, error_count)
    if normalized <= 1:
        return 30_000
    if normalized <= 2:
        return 60_000
    return 5 * 60_000


def resolve_profiles_unavailable_reason(
    store: AuthProfileStore,
    profile_ids: list[str],
    now: int | None = None,
) -> str | None:
    import time
    now = now or int(time.time() * 1000)
    scores: dict[str, int] = {}

    for profile_id in profile_ids:
        stats = store.get("usageStats", {}).get(profile_id)
        if not stats:
            continue

        disabled_until = stats.get("disabledUntil")
        if disabled_until and disabled_until > now:
            reason = stats.get("disabledReason", "")
            if reason in FAILURE_REASON_SET:
                scores[reason] = scores.get(reason, 0) + 1000
                continue

        blocked_until = stats.get("blockedUntil")
        if blocked_until and blocked_until > now:
            scores["rate_limit"] = scores.get("rate_limit", 0) + 1000
            continue

        cooldown_until = stats.get("cooldownUntil")
        if not cooldown_until or cooldown_until <= now:
            continue

        recorded = False
        for raw_reason, raw_count in stats.get("failureCounts", {}).items():
            reason = raw_reason
            count = raw_count if isinstance(raw_count, int) else 0
            if reason not in FAILURE_REASON_SET or count <= 0:
                continue
            scores[reason] = scores.get(reason, 0) + count
            recorded = True
        if not recorded:
            scores["unknown"] = scores.get("unknown", 0) + 1

    if not scores:
        return None

    best: str | None = None
    best_score = -1
    best_priority = float("inf")
    for reason in FAILURE_REASON_PRIORITY:
        score = scores.get(reason)
        if score is None:
            continue
        priority = FAILURE_REASON_ORDER.get(reason, float("inf"))
        if score > best_score or (score == best_score and priority < best_priority):
            best = reason
            best_score = score
            best_priority = priority
    return best


def mark_auth_profile_cooldown(
    store: AuthProfileStore,
    profile_id: str,
    agent_dir: str | None = None,
    run_id: str | None = None,
) -> None:
    mark_auth_profile_failure(
        store=store,
        profile_id=profile_id,
        reason="unknown",
        agent_dir=agent_dir,
        run_id=run_id,
    )


def mark_auth_profile_failure(
    store: AuthProfileStore,
    profile_id: str,
    reason: str,
    cfg: Any = None,
    agent_dir: str | None = None,
    run_id: str | None = None,
    model_id: str | None = None,
) -> None:
    profile = store.get("profiles", {}).get(profile_id)
    if not profile:
        return

    import time
    now = int(time.time() * 1000)
    prev_stats = store.get("usageStats", {}).get(profile_id, {})
    next_stats = _compute_next_profile_usage_stats(
        existing=prev_stats,
        now=now,
        reason=reason,
        model_id=model_id,
    )
    store.setdefault("usageStats", {})[profile_id] = next_stats

    from openclaw.agents.auth_profiles.store import save_auth_profile_store
    save_auth_profile_store(store, agent_dir)


def mark_auth_profile_blocked_until(
    store: AuthProfileStore,
    profile_id: str,
    blocked_until: int,
    source: AuthProfileBlockedSource,
    agent_dir: str | None = None,
    run_id: str | None = None,
    model_id: str | None = None,
) -> None:
    profile = store.get("profiles", {}).get(profile_id)
    if not profile:
        return

    import time
    now = int(time.time() * 1000)
    prev_stats = store.get("usageStats", {}).get(profile_id, {})
    active_blocked = prev_stats.get("blockedUntil", 0)
    if active_blocked and active_blocked > now:
        pass
    else:
        active_blocked = 0

    next_stats: ProfileUsageStats = {
        **prev_stats,
        "blockedUntil": max(active_blocked, blocked_until),
        "blockedReason": "subscription_limit",
        "blockedSource": source,
        "blockedModel": model_id,
        "cooldownUntil": None,
        "cooldownReason": None,
        "cooldownModel": None,
        "lastFailureAt": now,
        "failureCounts": {
            **prev_stats.get("failureCounts", {}),
            "rate_limit": prev_stats.get("failureCounts", {}).get("rate_limit", 0) + 1,
        },
    }
    store.setdefault("usageStats", {})[profile_id] = next_stats

    from openclaw.agents.auth_profiles.store import save_auth_profile_store
    save_auth_profile_store(store, agent_dir)


def _compute_next_profile_usage_stats(
    existing: ProfileUsageStats,
    now: int,
    reason: str,
    model_id: str | None = None,
) -> ProfileUsageStats:
    window_ms = 24 * 60 * 60 * 1000
    last_failure_at = existing.get("lastFailureAt", 0)
    window_expired = (
        isinstance(last_failure_at, int)
        and last_failure_at > 0
        and (now - last_failure_at) > window_ms
    )

    unusable_until = existing.get("cooldownUntil")
    if isinstance(unusable_until, int) and now >= unusable_until:
        previous_cooldown_expired = True
    else:
        previous_cooldown_expired = False

    should_reset = window_expired or previous_cooldown_expired
    base_error_count = 0 if should_reset else existing.get("errorCount", 0)
    next_error_count = base_error_count + 1
    failure_counts: dict[str, int] = {}
    if not should_reset:
        failure_counts = dict(existing.get("failureCounts", {}))
    failure_counts[reason] = failure_counts.get(reason, 0) + 1

    updated: ProfileUsageStats = {
        **existing,
        "errorCount": next_error_count,
        "failureCounts": failure_counts,
        "lastFailureAt": now,
    }

    if reason in ("billing", "auth_permanent"):
        base_ms = 5 * 60 * 60 * 1000 if reason == "billing" else 10 * 60 * 1000
        max_ms = 24 * 60 * 60 * 1000 if reason == "billing" else 60 * 60 * 1000
        disable_count = failure_counts.get(reason, 1)
        import math
        backoff = min(max_ms, base_ms * (2 ** min(disable_count - 1, 10)))
        existing_until = existing.get("disabledUntil")
        if isinstance(existing_until, int) and existing_until > now:
            updated["disabledUntil"] = existing_until
        else:
            updated["disabledUntil"] = now + backoff
        updated["disabledReason"] = reason
    else:
        backoff = calculate_auth_profile_cooldown_ms(next_error_count)
        existing_until = existing.get("cooldownUntil")
        if isinstance(existing_until, int) and existing_until > now:
            updated["cooldownUntil"] = existing_until
        else:
            updated["cooldownUntil"] = now + backoff
        updated["cooldownReason"] = reason
        if model_id and reason not in ("format", "billing", "auth", "server_error"):
            was_model_scoped = existing.get("cooldownModel")
            if was_model_scoped and was_model_scoped != model_id:
                updated["cooldownModel"] = None
            else:
                updated["cooldownModel"] = model_id
        else:
            updated["cooldownModel"] = None

    return updated


def clear_auth_profile_cooldown(
    store: AuthProfileStore,
    profile_id: str,
    agent_dir: str | None = None,
) -> None:
    if not store.get("usageStats", {}).get(profile_id):
        return
    store.setdefault("usageStats", {})[profile_id] = {
        "errorCount": 0,
        "blockedUntil": None,
        "blockedReason": None,
        "blockedSource": None,
        "blockedModel": None,
        "cooldownUntil": None,
        "cooldownReason": None,
        "cooldownModel": None,
        "disabledUntil": None,
        "disabledReason": None,
        "failureCounts": {},
    }
    from openclaw.agents.auth_profiles.store import save_auth_profile_store
    save_auth_profile_store(store, agent_dir)
