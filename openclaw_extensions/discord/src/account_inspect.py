"""Discord plugin module implements account inspect behavior."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from openclaw.config.secrets import normalize_secret_input_string
from openclaw.packages.normalization_core import normalize_optional_string
from openclaw.routing.account_id import DEFAULT_ACCOUNT_ID, normalize_account_id
from openclaw_extensions.discord.src.account_token_inspect import inspect_discord_configured_token
from openclaw_extensions.discord.src.accounts import (
    merge_discord_account_config,
    resolve_default_discord_account_id,
    resolve_discord_account_config,
)


@dataclass(frozen=True)
class InspectedDiscordAccount:
    account_id: str
    enabled: bool
    token: str
    token_source: str
    token_status: str
    configured: bool
    config: dict[str, Any]
    name: str | None = None


def inspect_discord_account(
    *,
    cfg: dict[str, Any],
    account_id: str | None = None,
    env_token: str | None = None,
) -> InspectedDiscordAccount:
    resolved_account_id = normalize_account_id(
        account_id or resolve_default_discord_account_id(cfg)
    )
    merged = merge_discord_account_config(cfg, resolved_account_id)
    discord = (cfg.get("channels") or {}).get("discord") or {}
    enabled = discord.get("enabled") is not False and merged.get("enabled") is not False
    account_config = resolve_discord_account_config(cfg, resolved_account_id)
    has_account_token = isinstance(account_config, dict) and "token" in account_config
    account_token = (
        inspect_discord_configured_token(account_config.get("token"))
        if isinstance(account_config, dict)
        else None
    )
    if account_token:
        return InspectedDiscordAccount(
            account_id=resolved_account_id,
            enabled=enabled,
            name=normalize_optional_string(merged.get("name")),
            token=account_token["token"],
            token_source=account_token["tokenSource"],
            token_status=account_token["tokenStatus"],
            configured=True,
            config=merged,
        )
    if has_account_token:
        return InspectedDiscordAccount(
            account_id=resolved_account_id,
            enabled=enabled,
            name=normalize_optional_string(merged.get("name")),
            token="",
            token_source="none",
            token_status="missing",
            configured=False,
            config=merged,
        )

    channel_token = inspect_discord_configured_token(discord.get("token"))
    if channel_token:
        return InspectedDiscordAccount(
            account_id=resolved_account_id,
            enabled=enabled,
            name=normalize_optional_string(merged.get("name")),
            token=channel_token["token"],
            token_source=channel_token["tokenSource"],
            token_status=channel_token["tokenStatus"],
            configured=True,
            config=merged,
        )

    allow_env = resolved_account_id == DEFAULT_ACCOUNT_ID
    resolved_env_token = (
        normalize_secret_input_string(env_token or os.environ.get("DISCORD_BOT_TOKEN"))
        if allow_env
        else None
    )
    if resolved_env_token:
        import re

        return InspectedDiscordAccount(
            account_id=resolved_account_id,
            enabled=enabled,
            name=normalize_optional_string(merged.get("name")),
            token=re.sub(r"^Bot\s+", "", resolved_env_token, flags=re.IGNORECASE),
            token_source="env",
            token_status="available",
            configured=True,
            config=merged,
        )

    return InspectedDiscordAccount(
        account_id=resolved_account_id,
        enabled=enabled,
        name=normalize_optional_string(merged.get("name")),
        token="",
        token_source="none",
        token_status="missing",
        configured=False,
        config=merged,
    )


__all__ = ["InspectedDiscordAccount", "inspect_discord_account"]
