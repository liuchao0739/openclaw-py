"""Merge configured direct, group, and pairing-store allowlists into effective lists."""

from __future__ import annotations

from typing import Any


def _normalize_string_entries(entries: list[Any] | None) -> list[str]:
    if not entries:
        return []
    result: list[str] = []
    for entry in entries:
        s = str(entry).strip() if entry is not None else ""
        if s:
            result.append(s)
    return result


def _merge_dm_allow_from_sources(
    allow_from: list[str] | None,
    store_allow_from: list[str] | None,
    dm_policy: str | None = None,
) -> list[str]:
    """Merge DM allowFrom sources based on policy."""
    if dm_policy in ("allowlist", "open"):
        return _normalize_string_entries(allow_from)
    merged: list[str] = []
    if allow_from:
        merged.extend(allow_from)
    if store_allow_from:
        merged.extend(store_allow_from)
    return _normalize_string_entries(merged)


def _resolve_group_allow_from_sources(
    allow_from: list[str] | None,
    group_allow_from: list[str] | None,
    fallback_to_allow_from: bool | None = None,
) -> list[str]:
    """Resolve group allowFrom sources with optional fallback to main allowFrom."""
    if group_allow_from:
        return _normalize_string_entries(group_allow_from)
    if fallback_to_allow_from is not False and allow_from:
        return _normalize_string_entries(allow_from)
    return []


def resolve_channel_ingress_effective_allow_from_lists(
    allow_from: list[Any] | None = None,
    group_allow_from: list[Any] | None = None,
    store_allow_from: list[Any] | None = None,
    dm_policy: str | None = None,
    group_allow_from_fallback_to_allow_from: bool | None = None,
) -> dict[str, list[str]]:
    """Merge configured direct, group, and pairing-store allowlists into effective lists."""
    af = allow_from if isinstance(allow_from, list) else None
    gaf = group_allow_from if isinstance(group_allow_from, list) else None
    saf = store_allow_from if isinstance(store_allow_from, list) else None

    effective_allow_from = _normalize_string_entries(
        _merge_dm_allow_from_sources(af, saf, dm_policy)
    )
    effective_group_allow_from = _normalize_string_entries(
        _resolve_group_allow_from_sources(af, gaf, group_allow_from_fallback_to_allow_from)
    )

    return {
        "effectiveAllowFrom": effective_allow_from,
        "effectiveGroupAllowFrom": effective_group_allow_from,
    }
