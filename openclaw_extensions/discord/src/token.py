import os
import re
from typing import Any, Dict, Optional


DiscordTokenSource = str

DISCORD_CREDENTIAL_STATUSES = ("available", "configured_unavailable", "missing")
DEFAULT_ACCOUNT_ID = "default"


class DiscordCredentialStatus:
    AVAILABLE = "available"
    CONFIGURED_UNAVAILABLE = "configured_unavailable"
    MISSING = "missing"


def normalize_account_id(account_id: Optional[str]) -> str:
    if not account_id or not str(account_id).strip():
        return DEFAULT_ACCOUNT_ID
    return str(account_id).strip()


def resolve_account_entry(accounts: Optional[Dict[str, Any]], account_id: str) -> Optional[Dict[str, Any]]:
    if not accounts:
        return None
    if account_id in accounts:
        return accounts[account_id]
    if DEFAULT_ACCOUNT_ID in accounts:
        return accounts[DEFAULT_ACCOUNT_ID]
    return None


def strip_discord_bot_prefix(token: str) -> str:
    return re.sub(r"^Bot\s+", "", token, flags=re.I)


def normalize_resolved_secret_input_string(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str):
        trimmed = value.strip()
        return trimmed or None
    if isinstance(value, dict):
        literal = value.get("literal")
        if isinstance(literal, str) and literal.strip():
            return literal.strip()
    return None


def resolve_secret_input_string(value: Any, defaults: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    if value is None:
        return {"status": "missing"}
    if isinstance(value, str):
        trimmed = value.strip()
        if trimmed:
            return {"status": "available", "value": trimmed}
        return {"status": "missing"}
    if isinstance(value, dict):
        if "literal" in value:
            literal = value.get("literal")
            if isinstance(literal, str) and literal.strip():
                return {"status": "available", "value": literal.strip()}
            return {"status": "missing"}
        if "ref" in value or "secretRef" in value:
            return {"status": "configured_unavailable"}
    return {"status": "missing"}


def normalize_discord_token(raw: Any) -> Optional[str]:
    trimmed = normalize_resolved_secret_input_string(raw)
    if not trimmed:
        return None
    return strip_discord_bot_prefix(trimmed)


def resolve_discord_token_value(value: Any) -> Dict[str, Any]:
    resolved = resolve_secret_input_string(value)
    if resolved["status"] == "available":
        return {"status": "available", "value": strip_discord_bot_prefix(resolved["value"])}
    if resolved["status"] == "configured_unavailable":
        return {"status": "configured_unavailable"}
    return {"status": "missing"}


def select_discord_runtime_config(cfg: Dict[str, Any]) -> Dict[str, Any]:
    return cfg


def resolve_discord_token(
    cfg: Dict[str, Any],
    opts: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    opts = opts or {}
    selected_cfg = select_discord_runtime_config(cfg)
    account_id = normalize_account_id(opts.get("accountId"))
    discord_cfg = (selected_cfg.get("channels") or {}).get("discord") or {}
    accounts = discord_cfg.get("accounts") or {}
    account_cfg = resolve_account_entry(accounts, account_id)
    has_account_token = account_cfg is not None and "token" in account_cfg

    account_token = resolve_discord_token_value(account_cfg.get("token") if account_cfg else None)
    if account_token["status"] == "available" and account_token.get("value"):
        return {"token": account_token["value"], "source": "config", "tokenStatus": "available"}
    if account_token["status"] == "configured_unavailable":
        return {"token": "", "source": "config", "tokenStatus": "configured_unavailable"}
    if has_account_token:
        return {"token": "", "source": "none", "tokenStatus": "missing"}

    config_token = resolve_discord_token_value(discord_cfg.get("token"))
    if config_token["status"] == "available" and config_token.get("value"):
        return {"token": config_token["value"], "source": "config", "tokenStatus": "available"}
    if config_token["status"] == "configured_unavailable":
        return {"token": "", "source": "config", "tokenStatus": "configured_unavailable"}

    allow_env = account_id == DEFAULT_ACCOUNT_ID
    env_token = None
    if allow_env:
        env_value = opts.get("envToken") or os.environ.get("DISCORD_BOT_TOKEN")
        env_token = normalize_discord_token(env_value)
    if env_token:
        return {"token": env_token, "source": "env", "tokenStatus": "available"}

    return {"token": "", "source": "none", "tokenStatus": "missing"}


class DiscordTokenResolution:
    def __init__(self, token: str, source: str, token_status: str):
        self.token = token
        self.source = source
        self.tokenStatus = token_status
