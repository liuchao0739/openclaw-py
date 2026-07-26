"""Directory config helper utilities.

Mirrors src/channels/plugins/directory-config-helpers.ts.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any, TypeVar

from openclaw.channels.plugins.directory_adapters import ChannelDirectoryEntry
from openclaw.packages.normalization_core import (
    normalize_lowercase_string_or_empty,
    normalize_optional_string,
)
from openclaw.plugins.contracts.shared import unique_strings

ResolvedAccount = TypeVar("ResolvedAccount")


def _resolve_directory_query(query: str | None) -> str:
    return normalize_lowercase_string_or_empty(query)


def _resolve_directory_limit(limit: int | None) -> int | None:
    return limit if isinstance(limit, int) and limit > 0 else None


def apply_directory_query_and_limit(
    ids: list[str],
    *,
    query: str | None = None,
    limit: int | None = None,
) -> list[str]:
    q = _resolve_directory_query(query)
    resolved_limit = _resolve_directory_limit(limit)
    filtered: list[str] = []
    for entry_id in ids:
        if q and q not in normalize_lowercase_string_or_empty(entry_id):
            continue
        filtered.append(entry_id)
        if resolved_limit is not None and len(filtered) >= resolved_limit:
            break
    return filtered


def to_directory_entries(kind: str, ids: list[str]) -> list[ChannelDirectoryEntry]:
    return [{"kind": kind, "id": entry_id} for entry_id in ids]


def _collect_directory_ids(
    values: Iterable[Any],
    normalize_id: Callable[[str], str | None] | None = None,
) -> list[str]:
    ids: list[str] = []
    for value in values:
        entry = normalize_optional_string(str(value)) or ""
        if not entry or entry == "*":
            continue
        normalized = normalize_id(entry) if normalize_id else entry
        entry_id = normalize_optional_string(normalized) or ""
        if entry_id:
            ids.append(entry_id)
    return ids


def _collect_directory_ids_from_map_keys(
    groups: dict[str, Any] | None,
    normalize_id: Callable[[str], str | None] | None = None,
) -> list[str]:
    return _collect_directory_ids((groups or {}).keys(), normalize_id)


def list_directory_user_entries_from_allow_from(
    *,
    allow_from: list[Any] | None = None,
    query: str | None = None,
    limit: int | None = None,
    normalize_id: Callable[[str], str | None] | None = None,
) -> list[ChannelDirectoryEntry]:
    ids = unique_strings(
        _collect_directory_ids(allow_from or [], normalize_id),
    )
    return to_directory_entries(
        "user", apply_directory_query_and_limit(ids, query=query, limit=limit)
    )


def list_directory_group_entries_from_map_keys(
    *,
    groups: dict[str, Any] | None = None,
    query: str | None = None,
    limit: int | None = None,
    normalize_id: Callable[[str], str | None] | None = None,
) -> list[ChannelDirectoryEntry]:
    ids = unique_strings(_collect_directory_ids_from_map_keys(groups, normalize_id))
    return to_directory_entries(
        "group",
        apply_directory_query_and_limit(ids, query=query, limit=limit),
    )


def list_resolved_directory_user_entries_from_allow_from(
    *,
    cfg: dict[str, Any],
    resolve_account: Callable[[dict[str, Any], str | None], ResolvedAccount],
    resolve_allow_from: Callable[[ResolvedAccount], list[Any] | None],
    account_id: str | None = None,
    query: str | None = None,
    limit: int | None = None,
    normalize_id: Callable[[str], str | None] | None = None,
) -> list[ChannelDirectoryEntry]:
    account = resolve_account(cfg, account_id)
    return list_directory_user_entries_from_allow_from(
        allow_from=resolve_allow_from(account),
        query=query,
        limit=limit,
        normalize_id=normalize_id,
    )


def list_resolved_directory_group_entries_from_map_keys(
    *,
    cfg: dict[str, Any],
    resolve_account: Callable[[dict[str, Any], str | None], ResolvedAccount],
    resolve_groups: Callable[[ResolvedAccount], dict[str, Any] | None],
    account_id: str | None = None,
    query: str | None = None,
    limit: int | None = None,
    normalize_id: Callable[[str], str | None] | None = None,
) -> list[ChannelDirectoryEntry]:
    account = resolve_account(cfg, account_id)
    return list_directory_group_entries_from_map_keys(
        groups=resolve_groups(account),
        query=query,
        limit=limit,
        normalize_id=normalize_id,
    )
