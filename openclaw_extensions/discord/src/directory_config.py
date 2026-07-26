"""Discord helper module supports directory config behavior."""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable
from typing import Any

from openclaw.channels.plugins.directory_config_helpers import (
    apply_directory_query_and_limit,
    to_directory_entries,
)
from openclaw.packages.normalization_core import normalize_optional_string
from openclaw.plugins.contracts.shared import unique_strings
from openclaw.routing.account_id import normalize_account_id
from openclaw_extensions.discord.src.accounts import (
    merge_discord_account_config,
    resolve_default_discord_account_id,
    resolve_discord_account_allow_from,
)


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


def _collect_normalized_directory_ids(
    *,
    sources: list[Iterable[Any]],
    normalize_id: Callable[[str], str | None],
) -> list[str]:
    ids: list[str] = []
    for source in sources:
        ids.extend(_collect_directory_ids(source, normalize_id))
    return unique_strings(ids)


def _list_directory_entries_from_sources(
    *,
    kind: str,
    sources: list[Iterable[Any]],
    query: str | None = None,
    limit: int | None = None,
    normalize_id: Callable[[str], str | None],
) -> list[dict[str, str]]:
    ids = _collect_normalized_directory_ids(sources=sources, normalize_id=normalize_id)
    return to_directory_entries(
        kind,
        apply_directory_query_and_limit(ids, query=query, limit=limit),
    )


def _resolve_discord_directory_config_account(
    cfg: dict[str, Any],
    account_id: str | None = None,
) -> dict[str, Any]:
    resolved_account_id = normalize_account_id(account_id or resolve_default_discord_account_id(cfg))
    config = merge_discord_account_config(cfg, resolved_account_id)
    return {
        "accountId": resolved_account_id,
        "config": config,
        "allowFrom": resolve_discord_account_allow_from(cfg=cfg, account_id=resolved_account_id)
        or [],
        "dm": config.get("dm"),
    }


def _normalize_discord_peer_id(raw: str) -> str | None:
    mention = re.match(r"^<@!?(\d+)>$", raw)
    cleaned = re.sub(r"^(discord|user):", "", mention.group(1) if mention else raw, flags=re.IGNORECASE).strip()
    return f"user:{cleaned}" if re.fullmatch(r"\d+", cleaned) else None


def _normalize_discord_group_id(raw: str) -> str | None:
    mention = re.match(r"^<#(\d+)>$", raw)
    cleaned = re.sub(
        r"^(discord|channel|group):",
        "",
        mention.group(1) if mention else raw,
        flags=re.IGNORECASE,
    ).strip()
    return f"channel:{cleaned}" if re.fullmatch(r"\d+", cleaned) else None


async def list_discord_directory_peers_from_config(params: dict[str, Any]) -> list[dict[str, str]]:
    account = _resolve_discord_directory_config_account(params["cfg"], params.get("accountId"))
    guild_users: list[Any] = []
    for guild in (account["config"].get("guilds") or {}).values():
        if not isinstance(guild, dict):
            continue
        guild_users.extend(guild.get("users") or [])
        for channel in (guild.get("channels") or {}).values():
            if isinstance(channel, dict):
                guild_users.extend(channel.get("users") or [])
    return _list_directory_entries_from_sources(
        kind="user",
        sources=[
            account["allowFrom"],
            list((account["config"].get("dms") or {}).keys()),
            guild_users,
        ],
        query=params.get("query"),
        limit=params.get("limit"),
        normalize_id=_normalize_discord_peer_id,
    )


async def list_discord_directory_groups_from_config(params: dict[str, Any]) -> list[dict[str, str]]:
    account = _resolve_discord_directory_config_account(params["cfg"], params.get("accountId"))
    channel_keys: list[Any] = []
    for guild in (account["config"].get("guilds") or {}).values():
        if isinstance(guild, dict):
            channel_keys.extend((guild.get("channels") or {}).keys())
    return _list_directory_entries_from_sources(
        kind="group",
        sources=[channel_keys],
        query=params.get("query"),
        limit=params.get("limit"),
        normalize_id=_normalize_discord_group_id,
    )


__all__ = [
    "list_discord_directory_groups_from_config",
    "list_discord_directory_peers_from_config",
]
