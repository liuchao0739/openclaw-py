"""Codex app-server rate-limit parsing helpers."""

from __future__ import annotations

from typing import Any

from openclaw.packages.normalization_core import (
    MAX_DATE_TIMESTAMP_MS,
    is_record,
    resolve_expires_at_ms_from_epoch_seconds,
)

CODEX_LIMIT_ID = "codex"
LIMIT_WINDOW_KEYS = ("primary", "secondary")
DAY_WINDOW_MINUTES = 24 * 60
WEEKLY_WINDOW_MINUTES = 7 * DAY_WINDOW_MINUTES
PROVIDER_LABELS = {"openai": "OpenAI"}


def _clamp_percent(value: float) -> float:
    return max(0.0, min(100.0, value))


def _read_number(record: dict[str, Any], key: str) -> float | None:
    value = record.get(key)
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    return None


def _is_rate_limit_snapshot(value: dict[str, Any]) -> bool:
    return any(
        key in value
        for key in (
            "primary",
            "secondary",
            "rateLimitReachedType",
            "rate_limit_reached_type",
            "limitId",
            "limit_id",
            "limitName",
            "limit_name",
        )
    )


def _read_rate_limit_window(snapshot: dict[str, Any], key: str) -> dict[str, Any] | None:
    window = snapshot.get(key)
    if not is_record(window):
        return None
    resets_at = _read_number(window, "resetsAt") or _read_number(window, "resets_at")
    resets_at_ms = resolve_expires_at_ms_from_epoch_seconds(
        resets_at,
        max_ms=MAX_DATE_TIMESTAMP_MS,
    ) or 0
    used_percent = _read_number(window, "usedPercent") or _read_number(window, "used_percent")
    window_duration = (
        _read_number(window, "windowDurationMins")
        or _read_number(window, "window_duration_mins")
        or _read_number(window, "windowMinutes")
        or _read_number(window, "window_minutes")
    )
    result: dict[str, Any] = {"resetsAtMs": int(resets_at_ms)}
    if used_percent is not None:
        result["usedPercent"] = used_percent
    if window_duration is not None:
        result["windowDurationMins"] = window_duration
    return result


def _sorted_rate_limit_keys(keys: list[str]) -> list[str]:
    return sorted(keys, key=lambda key: (0 if key == CODEX_LIMIT_ID else 1, key))


def _collect_rate_limit_snapshots(value: Any, snapshots: list[dict[str, Any]], seen: set[str]) -> None:
    if isinstance(value, list):
        for entry in value:
            _collect_rate_limit_snapshots(entry, snapshots, seen)
        return
    if not is_record(value):
        return
    if _is_rate_limit_snapshot(value):
        signature = "|".join(
            [
                str(value.get("limitId") or value.get("limit_id") or ""),
                str(value.get("limitName") or value.get("limit_name") or ""),
            ]
        )
        if signature not in seen:
            seen.add(signature)
            snapshots.append(value)
        return
    for key in ("rateLimitsByLimitId", "rate_limits_by_limit_id"):
        by_limit = value.get(key)
        if is_record(by_limit):
            for child_key in _sorted_rate_limit_keys(list(by_limit.keys())):
                _collect_rate_limit_snapshots(by_limit[child_key], snapshots, seen)
    for key in ("rateLimits", "rate_limits", "data", "items"):
        _collect_rate_limit_snapshots(value.get(key), snapshots, seen)


def _collect_codex_rate_limit_snapshots(value: Any) -> list[dict[str, Any]]:
    snapshots: list[dict[str, Any]] = []
    seen: set[str] = set()
    _collect_rate_limit_snapshots(value, snapshots, seen)
    return snapshots


def _is_codex_limit_snapshot(snapshot: dict[str, Any]) -> bool:
    limit_id = snapshot.get("limitId") or snapshot.get("limit_id")
    return limit_id == CODEX_LIMIT_ID


def _read_window_entries(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for key in LIMIT_WINDOW_KEYS:
        window = _read_rate_limit_window(snapshot, key)
        if window is not None:
            entries.append({"key": key, "window": window})
    return entries


def _format_provider_usage_window_label(entry: dict[str, Any], entries: list[dict[str, Any]]) -> str:
    window = entry["window"]
    minutes = window.get("windowDurationMins")
    if minutes == WEEKLY_WINDOW_MINUTES:
        return "Week"
    if minutes == DAY_WINDOW_MINUTES:
        return "Day"
    if isinstance(minutes, (int, float)) and 0 < minutes < DAY_WINDOW_MINUTES:
        if int(minutes) % 60 == 0:
            return f"{int(minutes) // 60}h"
        return f"{int(minutes)}m"
    if isinstance(minutes, (int, float)) and minutes > 0 and int(minutes) % DAY_WINDOW_MINUTES == 0:
        return f"{int(minutes) // DAY_WINDOW_MINUTES}d"
    if isinstance(minutes, (int, float)) and minutes > 0 and int(minutes) % 60 == 0:
        return f"{int(minutes) // 60}h"
    return "Short" if entry["key"] == "primary" else "Long"


def _read_provider_usage_window(entry: dict[str, Any], entries: list[dict[str, Any]]) -> dict[str, Any] | None:
    window = entry["window"]
    if window.get("usedPercent") is None and window.get("resetsAtMs", 0) <= 0:
        return None
    reset_at = window.get("resetsAtMs", 0)
    return {
        "label": _format_provider_usage_window_label(entry, entries),
        "usedPercent": _clamp_percent(float(window.get("usedPercent") or 0)),
        **({"resetAt": reset_at} if reset_at > 0 else {}),
    }


def _select_codex_provider_usage_snapshot(value: Any) -> dict[str, Any] | None:
    snapshots = _collect_codex_rate_limit_snapshots(value)
    for snapshot in snapshots:
        if _is_codex_limit_snapshot(snapshot):
            return snapshot
    return snapshots[0] if snapshots else None


def build_codex_app_server_usage_snapshot(value: Any) -> dict[str, Any]:
    """Convert Codex app-server rate-limit payloads into OpenAI/Codex usage windows."""
    snapshot = _select_codex_provider_usage_snapshot(value)
    entries = _read_window_entries(snapshot) if snapshot else []
    windows = [
        window
        for entry in entries
        if (window := _read_provider_usage_window(entry, entries)) is not None
    ]
    result: dict[str, Any] = {
        "provider": "openai",
        "displayName": PROVIDER_LABELS["openai"],
        "windows": windows,
    }
    return result
