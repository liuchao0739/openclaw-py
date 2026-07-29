from typing import Any, Dict, List


def collect_discord_security_audit_findings(cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    discord_cfg = (cfg.get("channels") or {}).get("discord") or {}
    accounts = discord_cfg.get("accounts") or {}
    for account_id, account in accounts.items():
        if not isinstance(account, dict):
            continue
        allow_from = account.get("allowFrom")
        if isinstance(allow_from, list) and "*" in allow_from:
            findings.append(
                {
                    "accountId": account_id,
                    "severity": "warn",
                    "message": "allowFrom contains wildcard '*' which permits all users",
                }
            )
        token = account.get("token")
        if isinstance(token, str) and token and not token.startswith("env:"):
            findings.append(
                {
                    "accountId": account_id,
                    "severity": "warn",
                    "message": "Bot token is stored as a literal value; prefer a secret reference",
                }
            )
    return findings
