from typing import Any, Dict, List, Optional


def list_discord_directory_peers_from_config(params: Dict[str, Any]) -> List[Dict[str, Any]]:
    cfg = params.get("cfg", {})
    discord_cfg = (cfg.get("channels") or {}).get("discord") or {}
    accounts = discord_cfg.get("accounts") or {}
    peers: List[Dict[str, Any]] = []
    for account_id, account in accounts.items():
        allow_from = account.get("allowFrom") if isinstance(account, dict) else None
        if isinstance(allow_from, list):
            for entry in allow_from:
                peers.append({"accountId": account_id, "id": str(entry)})
    return peers


def list_discord_directory_groups_from_config(params: Dict[str, Any]) -> List[Dict[str, Any]]:
    cfg = params.get("cfg", {})
    discord_cfg = (cfg.get("channels") or {}).get("discord") or {}
    accounts = discord_cfg.get("accounts") or {}
    groups: List[Dict[str, Any]] = []
    for account_id, account in accounts.items():
        default_to = account.get("defaultTo") if isinstance(account, dict) else None
        if default_to:
            groups.append({"accountId": account_id, "id": str(default_to)})
    return groups
