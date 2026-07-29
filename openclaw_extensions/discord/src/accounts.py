import re
from typing import Any, Dict, List, Optional

from .target_parsing import parse_discord_target
from .token import (
    DEFAULT_ACCOUNT_ID,
    normalize_account_id,
    resolve_account_entry,
    resolve_discord_token,
    DiscordCredentialStatus,
)


def normalize_optional_string(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str):
        trimmed = value.strip()
        return trimmed or None
    return None


class ResolvedDiscordAccount:
    def __init__(
        self,
        account_id: str,
        enabled: bool,
        token: str,
        token_source: str,
        token_status: str,
        config: Dict[str, Any],
        name: Optional[str] = None,
    ):
        self.accountId = account_id
        self.enabled = enabled
        self.name = name
        self.token = token
        self.tokenSource = token_source
        self.tokenStatus = token_status
        self.config = config


def list_discord_account_ids(cfg: Dict[str, Any]) -> List[str]:
    discord_cfg = (cfg.get("channels") or {}).get("discord") or {}
    accounts = discord_cfg.get("accounts") or {}
    if accounts:
        return list(accounts.keys())
    if discord_cfg.get("token") or normalize_optional_string(discord_cfg.get("token")):
        return [DEFAULT_ACCOUNT_ID]
    return []


def resolve_default_discord_account_id(cfg: Dict[str, Any]) -> str:
    ids = list_discord_account_ids(cfg)
    if not ids:
        return DEFAULT_ACCOUNT_ID
    if DEFAULT_ACCOUNT_ID in ids:
        return DEFAULT_ACCOUNT_ID
    return ids[0]


def resolve_discord_account_config(cfg: Dict[str, Any], account_id: str) -> Optional[Dict[str, Any]]:
    accounts = ((cfg.get("channels") or {}).get("discord") or {}).get("accounts") or {}
    return resolve_account_entry(accounts, account_id)


def merge_discord_account_config(cfg: Dict[str, Any], account_id: str) -> Dict[str, Any]:
    discord_cfg = (cfg.get("channels") or {}).get("discord") or {}
    accounts = discord_cfg.get("accounts") or {}
    base = {k: v for k, v in discord_cfg.items() if k != "accounts"}
    account = resolve_account_entry(accounts, account_id) or {}
    merged = dict(base)
    merged.update(account)
    return merged


def resolve_discord_account_allow_from(params: Dict[str, Any]) -> Optional[List[str]]:
    cfg = params["cfg"]
    account_id = normalize_account_id(params.get("accountId") or resolve_default_discord_account_id(cfg))
    account_config = resolve_discord_account_config(cfg, account_id) or {}
    root_config = (cfg.get("channels") or {}).get("discord") or {}
    allow_from = account_config.get("allowFrom") or root_config.get("allowFrom")
    if allow_from is None:
        return None
    if isinstance(allow_from, list):
        return [str(entry) for entry in allow_from]
    if isinstance(allow_from, str):
        return [allow_from]
    return None


def create_discord_action_gate(params: Dict[str, Any]):
    cfg = params["cfg"]
    account_id = normalize_account_id(params.get("accountId") or resolve_default_discord_account_id(cfg))
    discord_cfg = (cfg.get("channels") or {}).get("discord") or {}
    base_actions = discord_cfg.get("actions") or {}
    account_actions = (resolve_discord_account_config(cfg, account_id) or {}).get("actions") or {}
    merged = dict(base_actions)
    merged.update(account_actions)

    def gate(key: str, default_value: bool = False) -> bool:
        value = merged.get(key)
        if value is None:
            return default_value
        return bool(value)

    return gate


def resolve_discord_account(params: Dict[str, Any]) -> ResolvedDiscordAccount:
    cfg = params["cfg"]
    selected_cfg = cfg
    account_id = normalize_account_id(params.get("accountId") or resolve_default_discord_account_id(selected_cfg))
    base_enabled = (selected_cfg.get("channels") or {}).get("discord", {}).get("enabled", True) is not False
    merged = merge_discord_account_config(selected_cfg, account_id)
    account_enabled = merged.get("enabled", True) is not False
    enabled = base_enabled and account_enabled
    token_resolution = resolve_discord_token(selected_cfg, {"accountId": account_id})
    return ResolvedDiscordAccount(
        account_id=account_id,
        enabled=enabled,
        name=normalize_optional_string(merged.get("name")),
        token=token_resolution["token"],
        token_source=token_resolution["source"],
        token_status=token_resolution["tokenStatus"],
        config=merged,
    )


def resolve_discord_max_lines_per_message(params: Dict[str, Any]) -> Optional[int]:
    discord_config = params.get("discordConfig")
    if discord_config and isinstance(discord_config.get("maxLinesPerMessage"), int):
        return discord_config["maxLinesPerMessage"]
    account = resolve_discord_account(
        {"cfg": params["cfg"], "accountId": params.get("accountId")}
    )
    value = account.config.get("maxLinesPerMessage")
    return value if isinstance(value, int) else None


def resolve_discord_account_token_owner(params: Dict[str, Any]) -> Optional[str]:
    token = (params.get("token") or "").strip()
    if not token:
        return None
    owner: Optional[Dict[str, Any]] = None
    account_ids = list_discord_account_ids(params["cfg"])
    for index, account_id in enumerate(account_ids):
        account = resolve_discord_account({"cfg": params["cfg"], "accountId": account_id})
        account_token = account.token.strip()
        if not account.enabled or account_token != token:
            continue
        priority = 2 if account.tokenSource == "config" else 1 if account.tokenSource == "env" else 0
        if not owner or priority > owner["priority"]:
            owner = {"accountId": account.accountId, "priority": priority, "index": index}
            continue
        if priority == owner["priority"] and index < owner["index"]:
            owner = {"accountId": account.accountId, "priority": priority, "index": index}
    return owner["accountId"] if owner else None


def resolve_discord_duplicate_token_owner(params: Dict[str, Any]) -> Optional[str]:
    owner = resolve_discord_account_token_owner(
        {"cfg": params["cfg"], "token": params["account"].token}
    )
    return owner if owner and owner != params["account"].accountId else None


def is_discord_account_enabled_for_runtime(account: ResolvedDiscordAccount, cfg: Dict[str, Any]) -> bool:
    return account.enabled and not resolve_discord_duplicate_token_owner({"cfg": cfg, "account": account})


def resolve_discord_account_disabled_reason(account: ResolvedDiscordAccount, cfg: Dict[str, Any]) -> str:
    if not account.enabled:
        return "disabled"
    owner = resolve_discord_duplicate_token_owner({"cfg": cfg, "account": account})
    return f'duplicate bot token; using account "{owner}"' if owner else "disabled"


def list_enabled_discord_accounts(cfg: Dict[str, Any]) -> List[ResolvedDiscordAccount]:
    return [
        account
        for account in (
            resolve_discord_account({"cfg": cfg, "accountId": account_id})
            for account_id in list_discord_account_ids(cfg)
        )
        if is_discord_account_enabled_for_runtime(account, cfg)
    ]
