"""Channel allowlist resolution helpers.

Dedupes allowFrom entries and canonicalizes user lookups into stable id additions.
"""

from __future__ import annotations

from typing import Any


def _dedupe_allowlist_entries(entries: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for entry in entries:
        normalized = entry.strip()
        if not normalized:
            continue
        key = normalized.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(normalized)
    return deduped


def _map_allow_from_entries(existing: list[str | int] | None) -> list[str]:
    if not existing:
        return []
    result: list[str] = []
    for entry in existing:
        s = str(entry).strip() if entry is not None else ""
        if s:
            result.append(s)
    return result


def merge_allowlist(existing: list[str | int] | None, additions: list[str]) -> list[str]:
    """Merge existing allowlist entries with additions, deduping."""
    return _dedupe_allowlist_entries([*_map_allow_from_entries(existing), *additions])


def build_allowlist_resolution_summary(
    resolved_users: list[dict[str, Any]],
    format_resolved: Any = None,
    format_unresolved: Any = None,
) -> dict[str, Any]:
    """Split lookup results into resolved mappings, unresolved text, and id additions."""
    resolved_map = {entry["input"]: entry for entry in resolved_users}

    def _resolved_ok(entry: dict[str, Any]) -> bool:
        return bool(entry.get("resolved") and entry.get("id"))

    fmt_resolved = format_resolved or (lambda e: f"{e['input']}→{e['id']}")
    fmt_unresolved = format_unresolved or (lambda e: e["input"])

    mapping = [fmt_resolved(e) for e in resolved_users if _resolved_ok(e)]
    additions = [e["id"] for e in resolved_users if _resolved_ok(e) and e.get("id")]
    unresolved = [fmt_unresolved(e) for e in resolved_users if not _resolved_ok(e)]

    return {"resolvedMap": resolved_map, "mapping": mapping, "unresolved": unresolved, "additions": additions}


def canonicalize_allowlist_with_resolved_ids(
    existing: list[str | int] | None,
    resolved_map: dict[str, dict[str, Any]],
) -> list[str]:
    """Replace resolvable user entries with canonical ids while preserving unresolved entries and *."""
    canonicalized: list[str] = []
    for entry in existing or []:
        trimmed = str(entry).strip() if entry is not None else ""
        if not trimmed:
            continue
        if trimmed == "*":
            canonicalized.append(trimmed)
            continue
        resolved = resolved_map.get(trimmed)
        if resolved and resolved.get("resolved") and resolved.get("id"):
            canonicalized.append(resolved["id"])
        else:
            canonicalized.append(trimmed)
    return _dedupe_allowlist_entries(canonicalized)
