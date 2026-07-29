from copy import deepcopy
from typing import Any

from .accounts import DEFAULT_ACCOUNT_ID, resolve_default_feishu_account_id


def set_feishu_named_account_enabled(cfg: Any, account_id: str, enabled: bool) -> Any:
    if not isinstance(cfg, dict):
        cfg = {}
    result = deepcopy(cfg)
    channels = result.setdefault("channels", {})
    feishu_cfg = channels.get("feishu", {})
    if not isinstance(feishu_cfg, dict):
        feishu_cfg = {}
    accounts = feishu_cfg.get("accounts", {})
    if not isinstance(accounts, dict):
        accounts = {}
    account_entry = accounts.get(account_id, {})
    if not isinstance(account_entry, dict):
        account_entry = {}
    account_entry = dict(account_entry)
    account_entry["enabled"] = enabled
    accounts[account_id] = account_entry
    feishu_cfg["accounts"] = accounts
    channels["feishu"] = feishu_cfg
    result["channels"] = channels
    return result


def _resolve_account_id(params: dict) -> str:
    account_id = params.get("accountId")
    if isinstance(account_id, str) and account_id.strip():
        return account_id.strip()
    return resolve_default_feishu_account_id(params.get("cfg", {}))


def _apply_account_config(params: dict) -> Any:
    cfg = params.get("cfg", {})
    account_id = params.get("accountId")
    is_default = not account_id or account_id == DEFAULT_ACCOUNT_ID
    if is_default:
        if not isinstance(cfg, dict):
            cfg = {}
        result = deepcopy(cfg)
        channels = result.setdefault("channels", {})
        feishu_cfg = channels.get("feishu", {})
        if not isinstance(feishu_cfg, dict):
            feishu_cfg = {}
        feishu_cfg["enabled"] = True
        channels["feishu"] = feishu_cfg
        result["channels"] = channels
        return result
    return set_feishu_named_account_enabled(cfg, account_id, True)


feishu_setup_adapter = {
    "resolveAccountId": _resolve_account_id,
    "applyAccountConfig": _apply_account_config,
}
