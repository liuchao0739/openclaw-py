from __future__ import annotations

import hashlib
import json
import os
from typing import Any

from openclaw.agents.auth_profiles.constants import AUTH_STORE_VERSION
from openclaw.agents.auth_profiles.types import (
    AuthProfileBlockedReason,
    AuthProfileBlockedSource,
    AuthProfileFailureReason,
    AuthProfileState,
    AuthProfileStateStore,
    ProfileUsageStats,
)


AUTH_FAILURE_REASONS: set[str] = {
    "auth",
    "auth_permanent",
    "format",
    "overloaded",
    "rate_limit",
    "billing",
    "timeout",
    "model_not_found",
    "session_expired",
    "empty_response",
    "no_error_details",
    "unclassified",
    "unknown",
}

AUTH_BLOCKED_REASONS: set[str] = {"subscription_limit"}
AUTH_BLOCKED_SOURCES: set[str] = {"codex_rate_limits", "wham"}


def _normalize_finite_number(value: Any) -> int | None:
    if isinstance(value, (int, float)) and value > 0:
        return int(value)
    return None


def _normalize_enum_value(value: Any, allowed: set[str]) -> str | None:
    if not isinstance(value, str):
        return None
    return value if value in allowed else None


def _normalize_failure_counts(
    raw: Any,
) -> dict[str, int] | None:
    if not isinstance(raw, dict):
        return None
    normalized: dict[str, int] = {}
    for reason, count in raw.items():
        if reason not in AUTH_FAILURE_REASONS:
            continue
        if not isinstance(count, (int, float)) or count <= 0:
            continue
        normalized[reason] = int(count)
    return normalized or None


def _normalize_auth_profile_order(
    raw: Any,
) -> dict[str, list[str]] | None:
    if not isinstance(raw, dict):
        return None
    from openclaw.model_catalog_core.provider_id import normalize_provider_id
    from openclaw.normalization_core.string_normalization import unique_strings

    normalized: dict[str, list[str]] = {}
    for provider, value in raw.items():
        if not isinstance(value, list):
            continue
        provider_key = normalize_provider_id(provider)
        if not provider_key:
            continue
        list_val = unique_strings([v for v in value if isinstance(v, str)])
        if list_val:
            normalized[provider_key] = list_val
    return normalized or None


def _normalize_last_good(raw: Any) -> dict[str, str] | None:
    if not isinstance(raw, dict):
        return None
    from openclaw.model_catalog_core.provider_id import normalize_provider_id
    from openclaw.normalization_core.string_coerce import normalize_optional_string

    normalized: dict[str, str] = {}
    for provider, profile_id in raw.items():
        provider_key = normalize_provider_id(provider)
        normalized_id = normalize_optional_string(profile_id)
        if provider_key and normalized_id:
            normalized[provider_key] = normalized_id
    return normalized or None


def _normalize_usage_stats_entry(raw: Any) -> ProfileUsageStats | None:
    if not isinstance(raw, dict):
        return None
    stats: ProfileUsageStats = {}
    if "lastUsed" in raw:
        val = _normalize_finite_number(raw["lastUsed"])
        if val is not None:
            stats["lastUsed"] = val
    if "blockedUntil" in raw:
        val = _normalize_finite_number(raw["blockedUntil"])
        if val is not None:
            stats["blockedUntil"] = val
    if "blockedReason" in raw:
        val = _normalize_enum_value(raw["blockedReason"], AUTH_BLOCKED_REASONS)
        if val:
            stats["blockedReason"] = val
    if "blockedSource" in raw:
        val = _normalize_enum_value(raw["blockedSource"], AUTH_BLOCKED_SOURCES)
        if val:
            stats["blockedSource"] = val
    if "blockedModel" in raw and isinstance(raw["blockedModel"], str):
        stats["blockedModel"] = raw["blockedModel"]
    if "cooldownUntil" in raw:
        val = _normalize_finite_number(raw["cooldownUntil"])
        if val is not None:
            stats["cooldownUntil"] = val
    if "cooldownReason" in raw:
        val = _normalize_enum_value(raw["cooldownReason"], AUTH_FAILURE_REASONS)
        if val:
            stats["cooldownReason"] = val
    if "cooldownModel" in raw and isinstance(raw["cooldownModel"], str):
        stats["cooldownModel"] = raw["cooldownModel"]
    if "disabledUntil" in raw:
        val = _normalize_finite_number(raw["disabledUntil"])
        if val is not None:
            stats["disabledUntil"] = val
    if "disabledReason" in raw:
        val = _normalize_enum_value(raw["disabledReason"], AUTH_FAILURE_REASONS)
        if val:
            stats["disabledReason"] = val
    if "errorCount" in raw:
        val = _normalize_finite_number(raw["errorCount"])
        if val is not None:
            stats["errorCount"] = val
    if "failureCounts" in raw:
        val = _normalize_failure_counts(raw["failureCounts"])
        if val:
            stats["failureCounts"] = val
    if "lastFailureAt" in raw:
        val = _normalize_finite_number(raw["lastFailureAt"])
        if val is not None:
            stats["lastFailureAt"] = val

    keys_to_check = [
        "lastUsed", "blockedUntil", "blockedReason", "blockedSource",
        "blockedModel", "cooldownUntil", "cooldownReason", "cooldownModel",
        "disabledUntil", "disabledReason", "errorCount", "failureCounts",
        "lastFailureAt",
    ]
    has_any = any(k in stats for k in keys_to_check)
    return stats if has_any else None


def _normalize_usage_stats(
    raw: Any,
) -> dict[str, ProfileUsageStats] | None:
    if not isinstance(raw, dict):
        return None
    normalized: dict[str, ProfileUsageStats] = {}
    for profile_id, value in raw.items():
        from openclaw.normalization_core.string_coerce import normalize_optional_string
        normalized_id = normalize_optional_string(profile_id)
        stats = _normalize_usage_stats_entry(value)
        if normalized_id and stats:
            normalized[normalized_id] = stats
    return normalized or None


def coerce_auth_profile_state(raw: Any) -> AuthProfileState:
    if not isinstance(raw, dict):
        return {}
    result: AuthProfileState = {}
    order = _normalize_auth_profile_order(raw.get("order"))
    if order:
        result["order"] = order
    last_good = _normalize_last_good(raw.get("lastGood"))
    if last_good:
        result["lastGood"] = last_good
    usage_stats = _normalize_usage_stats(raw.get("usageStats"))
    if usage_stats:
        result["usageStats"] = usage_stats
    return result


def merge_auth_profile_state(
    base: AuthProfileState,
    override: AuthProfileState,
) -> AuthProfileState:
    def _merge_record(
        left: dict[str, Any] | None,
        right: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        if not left and not right:
            return None
        if not left:
            return dict(right)
        if not right:
            return dict(left)
        return {**left, **right}

    result: AuthProfileState = {}
    order = _merge_record(base.get("order"), override.get("order"))
    if order:
        result["order"] = order
    last_good = _merge_record(base.get("lastGood"), override.get("lastGood"))
    if last_good:
        result["lastGood"] = last_good
    usage_stats = _merge_record(base.get("usageStats"), override.get("usageStats"))
    if usage_stats:
        result["usageStats"] = usage_stats
    return result


def load_persisted_auth_profile_state(
    agent_dir: str | None = None,
    database: Any = None,
) -> AuthProfileState:
    from openclaw.agents.auth_profiles.sqlite import (
        read_persisted_auth_profile_state_raw,
    )
    return coerce_auth_profile_state(
        read_persisted_auth_profile_state_raw(agent_dir, database)
    )


def build_persisted_auth_profile_state(
    store: AuthProfileState,
) -> AuthProfileStateStore | None:
    state = coerce_auth_profile_state(store)
    if not state.get("order") and not state.get("lastGood") and not state.get("usageStats"):
        return None
    result: AuthProfileStateStore = {"version": AUTH_STORE_VERSION}
    if state.get("order"):
        result["order"] = state["order"]
    if state.get("lastGood"):
        result["lastGood"] = state["lastGood"]
    if state.get("usageStats"):
        result["usageStats"] = state["usageStats"]
    return result


def save_persisted_auth_profile_state(
    store: AuthProfileState,
    agent_dir: str | None = None,
) -> AuthProfileStateStore | None:
    payload = build_persisted_auth_profile_state(store)
    from openclaw.agents.auth_profiles.sqlite import (
        read_persisted_auth_profile_state_raw,
        write_persisted_auth_profile_state_raw,
    )
    existing_raw = read_persisted_auth_profile_state_raw(agent_dir)
    if payload and json.dumps(existing_raw, sort_keys=True) != json.dumps(payload, sort_keys=True):
        write_persisted_auth_profile_state_raw(payload, agent_dir)
    return payload
