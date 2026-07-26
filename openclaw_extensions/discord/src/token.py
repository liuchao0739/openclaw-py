"""Discord plugin module implements token behavior."""

from __future__ import annotations

import os
from typing import Any, Literal

from openclaw.config.secrets import coerce_secret_ref, normalize_secret_input_string
from openclaw.routing.account_id import DEFAULT_ACCOUNT_ID, normalize_account_id
from openclaw.routing.account_lookup import resolve_account_entry
from openclaw_extensions.discord.src.runtime_config import select_discord_runtime_config

DiscordCredentialStatus = Literal["available", "configured_unavailable", "missing"]
DiscordTokenSource = Literal["env", "config", "none"]


def _strip_discord_bot_prefix(token: str) -> str:
    import re

    return re.sub(r"^Bot\s+", "", token, flags=re.IGNORECASE)


def normalize_discord_token(raw: object, path: str) -> str | None:
    normalized = normalize_secret_input_string(raw)
    if not normalized:
        return None
    return _strip_discord_bot_prefix(normalized)


def _resolve_discord_token_value(
    *,
    cfg: dict[str, Any],
    value: object,
    path: str,
) -> dict[str, str]:
    if coerce_secret_ref(value):
        return {"status": "configured_unavailable"}
    normalized = normalize_secret_input_string(value)
    if normalized:
        return {"status": "available", "value": _strip_discord_bot_prefix(normalized)}
    if value is not None and value != "":
        return {"status": "missing"}
    return {"status": "missing"}


def resolve_discord_token(
    cfg: dict[str, Any],
    opts: dict[str, Any] | None = None,
) -> dict[str, str]:
    opts = opts or {}
    selected_cfg = select_discord_runtime_config(cfg)
    account_id = normalize_account_id(opts.get("accountId"))
    discord_cfg = (selected_cfg.get("channels") or {}).get("discord") or {}
    account_cfg = resolve_account_entry(discord_cfg.get("accounts"), account_id)
    has_account_token = isinstance(account_cfg, dict) and "token" in account_cfg
    account_token = _resolve_discord_token_value(
        cfg=selected_cfg,
        value=account_cfg.get("token") if isinstance(account_cfg, dict) else None,
        path=f"channels.discord.accounts.{account_id}.token",
    )
    if account_token["status"] == "available" and account_token.get("value"):
        return {
            "token": account_token["value"],
            "source": "config",
            "tokenStatus": "available",
        }
    if account_token["status"] == "configured_unavailable":
        return {"token": "", "source": "config", "tokenStatus": "configured_unavailable"}
    if has_account_token:
        return {"token": "", "source": "none", "tokenStatus": "missing"}

    config_token = _resolve_discord_token_value(
        cfg=selected_cfg,
        value=discord_cfg.get("token"),
        path="channels.discord.token",
    )
    if config_token["status"] == "available" and config_token.get("value"):
        return {
            "token": config_token["value"],
            "source": "config",
            "tokenStatus": "available",
        }
    if config_token["status"] == "configured_unavailable":
        return {"token": "", "source": "config", "tokenStatus": "configured_unavailable"}

    allow_env = account_id == DEFAULT_ACCOUNT_ID
    env_token = (
        normalize_discord_token(opts.get("envToken") or os.environ.get("DISCORD_BOT_TOKEN"), "")
        if allow_env
        else None
    )
    if env_token:
        return {"token": env_token, "source": "env", "tokenStatus": "available"}

    return {"token": "", "source": "none", "tokenStatus": "missing"}


__all__ = [
    "DiscordCredentialStatus",
    "DiscordTokenSource",
    "normalize_discord_token",
    "resolve_discord_token",
]
