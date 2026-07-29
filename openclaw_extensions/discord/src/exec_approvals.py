from typing import Any, Dict, List, Optional


def get_discord_exec_approval_approvers(cfg: Dict[str, Any], account_id: str) -> List[str]:
    discord_cfg = (cfg.get("channels") or {}).get("discord") or {}
    accounts = discord_cfg.get("accounts") or {}
    account = accounts.get(account_id, {})
    approvers = account.get("execApproval", {}).get("approvers") if isinstance(account, dict) else None
    return list(approvers or [])


def is_discord_exec_approval_approver(cfg: Dict[str, Any], account_id: str, user_id: str) -> bool:
    approvers = get_discord_exec_approval_approvers(cfg, account_id)
    return user_id in approvers


def is_discord_exec_approval_client_enabled(cfg: Dict[str, Any], account_id: str) -> bool:
    discord_cfg = (cfg.get("channels") or {}).get("discord") or {}
    accounts = discord_cfg.get("accounts") or {}
    account = accounts.get(account_id, {})
    if not isinstance(account, dict):
        return False
    return bool(account.get("execApproval", {}).get("clientEnabled", False))


def should_suppress_local_discord_exec_approval_prompt(params: Dict[str, Any]) -> bool:
    cfg = params.get("cfg", {})
    account_id = params.get("accountId", "default")
    return is_discord_exec_approval_client_enabled(cfg, account_id)
