from __future__ import annotations

from openclaw.plugin_sdk.doctor_runtime import (
    create_health_check_contract,
)
from openclaw.plugin_sdk.string_coerce_runtime import (
    normalize_lowercase_string_or_empty,
    normalize_optional_string,
)
from openclaw_extensions.googlechat.src.accounts import (
    ResolvedGoogleChatAccount,
    resolve_google_chat_account,
)
from openclaw_extensions.googlechat.src.api import (
    fetch_google_chat_credentials_with_logs,
    test_google_chat_send_support,
)


def _resolve_doctor_account(params: dict) -> ResolvedGoogleChatAccount | None:
    account = resolve_google_chat_account(
        cfg=params.get("cfg"),
        account_id=params.get("accountId"),
    )
    return account if account.enabled and account.credential_source != "none" else None


def _credential_health_check(params: dict) -> dict:
    account = _resolve_doctor_account(params)
    if not account:
        return {
            "level": "warn",
            "message": "Google Chat credentials not configured or account disabled",
            "detail": {},
        }
    try:
        credentials = fetch_google_chat_credentials_with_logs({"account": account})
        if credentials:
            return {
                "level": "ok",
                "message": "Google Chat credentials resolved",
                "detail": {"credentialSource": account.credential_source},
            }
        return {
            "level": "warn",
            "message": "Google Chat credentials not available",
            "detail": {"credentialSource": account.credential_source},
        }
    except Exception as error:
        return {
            "level": "fail",
            "message": f"Google Chat credentials error: {error}",
            "detail": {"credentialSource": account.credential_source},
        }


def _webhook_health_check(params: dict) -> dict:
    account = _resolve_doctor_account(params)
    if not account:
        return {
            "level": "warn",
            "message": "Google Chat webhook not configured",
            "detail": {},
        }
    audience = normalize_optional_string(account.config.get("audience"))
    if not audience:
        return {
            "level": "warn",
            "message": "Google Chat audience not configured",
            "detail": {},
        }
    audience_type = normalize_lowercase_string_or_empty(account.config.get("audienceType"))
    app_principal = normalize_optional_string(account.config.get("appPrincipal"))
    if audience_type == "app-url" and not app_principal:
        return {
            "level": "warn",
            "message": "Google Chat appPrincipal missing for app-url audience",
            "detail": {"audienceType": audience_type},
        }
    return {
        "level": "ok",
        "message": "Google Chat webhook identity configured",
        "detail": {"audienceType": audience_type, "audience": audience},
    }


async def _send_health_check(params: dict) -> dict:
    account = _resolve_doctor_account(params)
    if not account:
        return {
            "level": "warn",
            "message": "Google Chat send test skipped: account not configured",
            "detail": {},
        }
    try:
        result = await test_google_chat_send_support({"account": account})
        return {
            "level": "ok" if result.get("ok") else "warn",
            "message": result.get("message", "Send test completed"),
            "detail": result,
        }
    except Exception as error:
        return {
            "level": "fail",
            "message": f"Google Chat send test failed: {error}",
            "detail": {},
        }


GOOGLE_CHAT_DOCTOR_CONTRACT = create_health_check_contract({
    "credential": _credential_health_check,
    "webhook": _webhook_health_check,
    "send": _send_health_check,
})


def run_google_chat_doctor(params: dict) -> dict:
    return GOOGLE_CHAT_DOCTOR_CONTRACT.run(params)


__all__ = [
    "GOOGLE_CHAT_DOCTOR_CONTRACT",
    "run_google_chat_doctor",
]