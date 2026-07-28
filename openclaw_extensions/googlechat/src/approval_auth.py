from __future__ import annotations

from openclaw.plugin_sdk.approval_auth_runtime import (
    create_resolved_approver_action_auth_adapter,
    resolve_approval_approvers,
)
from openclaw.plugin_sdk.string_coerce_runtime import normalize_lowercase_string_or_empty
from openclaw_extensions.googlechat.src.accounts import resolve_google_chat_account
from openclaw_extensions.googlechat.src.targets import (
    is_google_chat_user_target,
    normalize_google_chat_target,
)


def normalize_google_chat_approver_id(value: str | int) -> str | None:
    normalized = normalize_google_chat_target(str(value))
    if not normalized or not is_google_chat_user_target(normalized):
        return None
    suffix = normalize_lowercase_string_or_empty(normalized[len("users/"):])
    if not suffix or "@" in suffix:
        return None
    return f"users/{suffix}"


def get_google_chat_approval_approvers(params: dict) -> list[str]:
    account = resolve_google_chat_account(
        cfg=params.get("cfg"),
        account_id=params.get("accountId"),
    )
    return resolve_approval_approvers({
        "allowFrom": (account.config.get("dm") or {}).get("allowFrom"),
        "defaultTo": account.config.get("defaultTo"),
        "normalizeApprover": normalize_google_chat_approver_id,
    })


google_chat_approval_auth = create_resolved_approver_action_auth_adapter({
    "channelLabel": "Google Chat",
    "resolveApprovers": get_google_chat_approval_approvers,
    "normalizeSenderId": lambda value: normalize_google_chat_approver_id(value),
})

__all__ = [
    "normalize_google_chat_approver_id",
    "get_google_chat_approval_approvers",
    "google_chat_approval_auth",
]