"""Direct-message allowlist audit state.

Merges configured and persisted allowFrom entries for setup/status prompts.
"""

from __future__ import annotations

from typing import Any, Callable

from openclaw.channels.message_access.store_allow_from import (
    read_channel_ingress_store_allow_from_for_dm_policy,
)


def _normalize_string_entries(entries: list[Any] | None) -> list[str]:
    if not entries:
        return []
    result: list[str] = []
    for entry in entries:
        s = str(entry).strip() if entry is not None else ""
        if s:
            result.append(s)
    return result


async def resolve_dm_allow_audit_state(
    provider: str,
    account_id: str,
    allow_from: list[Any] | None = None,
    dm_policy: str | None = None,
    normalize_entry: Callable[[str], str] | None = None,
    read_store: Callable[[str, str], Any] | None = None,
) -> dict[str, Any]:
    """Resolve DM allow audit state from configured and store allowFrom entries."""
    config_allow_from = _normalize_string_entries(
        allow_from if isinstance(allow_from, list) else None
    )
    has_wildcard = "*" in config_allow_from

    store_allow_from = await read_channel_ingress_store_allow_from_for_dm_policy(
        provider, account_id, dm_policy, read_store=read_store,
    )

    norm = normalize_entry or (lambda v: v)
    normalized_cfg = _normalize_string_entries(
        [norm(v) for v in config_allow_from if v != "*"]
    )
    normalized_store = _normalize_string_entries(
        [norm(v) for v in store_allow_from]
    )

    allow_count = len(set([*normalized_cfg, *normalized_store]))

    return {
        "configAllowFrom": config_allow_from,
        "hasWildcard": has_wildcard,
        "allowCount": allow_count,
        "isMultiUserDm": has_wildcard or allow_count > 1,
    }
