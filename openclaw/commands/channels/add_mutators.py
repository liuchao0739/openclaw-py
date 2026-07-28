from __future__ import annotations

from typing import Any


def _resolve_default_account_id(config: dict[str, Any]) -> str | None:
    accounts = config.get("accounts") or {}
    for account_id, account in accounts.items():
        if isinstance(account, dict) and account.get("isDefault"):
            return account_id
    return None


def _apply_account_name(config: dict[str, Any], channel: str, account_id: str, name: str) -> dict[str, Any]:
    channels = config.get("channels") or {}
    channel_config = channels.get(channel) or {}
    accounts = channel_config.get("accounts") or {}
    account = accounts.get(account_id) or {}
    account["name"] = name
    accounts[account_id] = account
    channel_config["accounts"] = accounts
    channels[channel] = channel_config
    config["channels"] = channels
    return config
