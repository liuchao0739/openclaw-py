from typing import Any, Dict, List

from .accounts import (
    is_discord_account_enabled_for_runtime,
    list_discord_account_ids,
    resolve_discord_account,
)


def collect_discord_status_issues(cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    issues: List[Dict[str, Any]] = []
    for account_id in list_discord_account_ids(cfg):
        account = resolve_discord_account({"cfg": cfg, "accountId": account_id})
        if not account.enabled:
            issues.append(
                {
                    "accountId": account_id,
                    "severity": "error",
                    "message": "account is disabled",
                }
            )
            continue
        if not is_discord_account_enabled_for_runtime(account, cfg):
            issues.append(
                {
                    "accountId": account_id,
                    "severity": "warn",
                    "message": "account disabled due to duplicate token",
                }
            )
        if account.tokenStatus == "missing":
            issues.append(
                {
                    "accountId": account_id,
                    "severity": "error",
                    "message": "missing Discord bot token",
                }
            )
        elif account.tokenStatus == "configured_unavailable":
            issues.append(
                {
                    "accountId": account_id,
                    "severity": "warn",
                    "message": "token configured but secret unavailable at runtime",
                }
            )
    return issues
