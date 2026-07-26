"""Discord plugin module implements accounts behavior."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from openclaw.channels.plugins.account_action_gate import create_account_action_gate
from openclaw.channels.plugins.account_helpers import (
    create_account_list_helpers,
    resolve_merged_account_config,
)
from openclaw.packages.normalization_core import normalize_optional_string
from openclaw.routing.account_id import normalize_account_id
from openclaw.routing.account_lookup import resolve_account_entry
from openclaw_extensions.discord.src.runtime_config import select_discord_runtime_config
from openclaw_extensions.discord.src.token import resolve_discord_token

_account_helpers = create_account_list_helpers(
    "discord",
    implicit_default_account={
        "channelKeys": ["token"],
        "envVars": ["DISCORD_BOT_TOKEN"],
    },
)
list_discord_account_ids = _account_helpers["list_account_ids"]
resolve_default_discord_account_id = _account_helpers["resolve_default_account_id"]


@dataclass(frozen=True)
class ResolvedDiscordAccount:
    account_id: str
    enabled: bool
    token: str
    token_source: str
    token_status: str
    config: dict[str, Any]
    name: str | None = None


def resolve_discord_account_config(cfg: dict[str, Any], account_id: str) -> dict[str, Any] | None:
    discord = (cfg.get("channels") or {}).get("discord") or {}
    return resolve_account_entry(discord.get("accounts"), account_id)


def merge_discord_account_config(cfg: dict[str, Any], account_id: str) -> dict[str, Any]:
    discord = (cfg.get("channels") or {}).get("discord") or {}
    return resolve_merged_account_config(
        channel_config=discord,
        accounts=discord.get("accounts"),
        account_id=account_id,
        nested_object_keys=["agentComponents", "botLoopProtection"],
    )


def _read_allow_from(record: dict[str, Any] | None) -> list[Any] | None:
    if not isinstance(record, dict):
        return None
    dm = record.get("dm")
    if isinstance(dm, dict) and isinstance(dm.get("allowFrom"), list):
        return dm["allowFrom"]
    if isinstance(record.get("allowFrom"), list):
        return record["allowFrom"]
    return None


def resolve_discord_account_allow_from(
    *,
    cfg: dict[str, Any],
    account_id: str | None = None,
) -> list[str] | None:
    resolved_account_id = normalize_account_id(
        account_id or resolve_default_discord_account_id(cfg)
    )
    account_config = resolve_discord_account_config(cfg, resolved_account_id)
    root_config = (cfg.get("channels") or {}).get("discord") or {}
    allow_from = _read_allow_from(account_config) or _read_allow_from(root_config)
    if not allow_from:
        return None
    return [str(entry).strip() for entry in allow_from if str(entry).strip()]


def create_discord_action_gate(
    *,
    cfg: dict[str, Any],
    account_id: str | None = None,
):
    resolved_account_id = normalize_account_id(
        account_id or resolve_default_discord_account_id(cfg)
    )
    discord = (cfg.get("channels") or {}).get("discord") or {}
    account_config = resolve_discord_account_config(cfg, resolved_account_id) or {}
    return create_account_action_gate(
        base_actions=discord.get("actions"),
        account_actions=account_config.get("actions"),
    )


def resolve_discord_account(
    *,
    cfg: dict[str, Any],
    account_id: str | None = None,
) -> ResolvedDiscordAccount:
    selected = select_discord_runtime_config(cfg)
    resolved_account_id = normalize_account_id(
        account_id or resolve_default_discord_account_id(selected)
    )
    discord = (selected.get("channels") or {}).get("discord") or {}
    base_enabled = discord.get("enabled") is not False
    merged = merge_discord_account_config(selected, resolved_account_id)
    account_enabled = merged.get("enabled") is not False
    enabled = base_enabled and account_enabled
    token_resolution = resolve_discord_token(selected, {"accountId": resolved_account_id})
    return ResolvedDiscordAccount(
        account_id=resolved_account_id,
        enabled=enabled,
        name=normalize_optional_string(merged.get("name")),
        token=token_resolution["token"],
        token_source=token_resolution["source"],
        token_status=token_resolution["tokenStatus"],
        config=merged,
    )


__all__ = [
    "ResolvedDiscordAccount",
    "create_discord_action_gate",
    "list_discord_account_ids",
    "merge_discord_account_config",
    "resolve_default_discord_account_id",
    "resolve_discord_account",
    "resolve_discord_account_allow_from",
    "resolve_discord_account_config",
]
