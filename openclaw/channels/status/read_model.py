"""Read-model helpers that merge gateway channel status with local config snapshots."""

from __future__ import annotations

from typing import Any

DEFAULT_ACCOUNT_ID = "default"

CREDENTIAL_STATUS_KEYS = (
    "tokenStatus",
    "botTokenStatus",
    "appTokenStatus",
    "signingSecretStatus",
    "userTokenStatus",
)


def _as_record(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {}


def _read_runtime_accounts_by_channel(payload: Any) -> dict[str, Any]:
    return _as_record(_as_record(payload).get("channelAccounts"))


def get_runtime_channel_accounts(payload: Any, channel_id: str) -> list[dict[str, Any]]:
    """Read raw runtime account records for one channel from a gateway payload."""
    raw = _read_runtime_accounts_by_channel(payload).get(channel_id)
    if not isinstance(raw, list):
        return []
    return [_as_record(item) for item in raw]


def normalize_runtime_channel_account_snapshots(payload: Any) -> dict[str, list[dict[str, Any]]]:
    """Normalize gateway channel account snapshots into a channel-id map."""
    out: dict[str, list[dict[str, Any]]] = {}
    for channel_id, accounts in _read_runtime_accounts_by_channel(payload).items():
        if not isinstance(accounts, list):
            continue
        normalized = [
            acc for acc in accounts
            if isinstance(acc, dict) and isinstance(acc.get("accountId"), str)
        ]
        if normalized:
            out[channel_id] = normalized
    return out


def _resolve_runtime_channel_account_id(account: dict[str, Any]) -> str:
    for key in ("accountId", "id", "name"):
        val = account.get(key)
        if val and isinstance(val, str) and val.strip():
            return val.strip()
    return DEFAULT_ACCOUNT_ID


def _find_runtime_channel_account(live_accounts: list[dict[str, Any]], account_id: str) -> dict[str, Any] | None:
    for account in live_accounts:
        if _resolve_runtime_channel_account_id(account) == account_id:
            return account
    if account_id == DEFAULT_ACCOUNT_ID and len(live_accounts) == 1:
        return live_accounts[0]
    return None


def has_runtime_credential_available(live_accounts: list[dict[str, Any]], account_id: str) -> bool:
    """Report whether a runtime account has usable live credentials."""
    account = _find_runtime_channel_account(live_accounts, account_id)
    if not account:
        return False
    for key in CREDENTIAL_STATUS_KEYS:
        if account.get(key) == "configured_unavailable":
            return False
    return account.get("running") is True or account.get("connected") is True


def mark_configured_unavailable_credential_statuses_available(account: Any) -> dict[str, Any]:
    """Convert configured-but-unavailable credential markers to available."""
    record = dict(_as_record(account))
    for key in CREDENTIAL_STATUS_KEYS:
        if record.get(key) == "configured_unavailable":
            record[key] = "available"
    return record
