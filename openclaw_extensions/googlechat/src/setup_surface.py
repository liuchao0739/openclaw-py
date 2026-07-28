from __future__ import annotations

import os
from typing import Any

from openclaw.plugin_sdk.runtime_env import create_subsystem_logger
from openclaw.plugin_sdk.setup_runtime import (
    create_setup_translator,
    create_standard_channel_setup_status,
)
from openclaw.plugin_sdk.string_coerce_runtime import (
    normalize_lowercase_string_or_empty,
    normalize_optional_string,
    normalize_stringified_optional_string,
)
from openclaw_extensions.googlechat.src.accounts import (
    list_google_chat_account_ids,
    resolve_default_google_chat_account_id,
    resolve_google_chat_account,
)

log = create_subsystem_logger("googlechat/setup")
t = create_setup_translator()

channel = "googlechat"
DEFAULT_ACCOUNT_ID = "default"
ENV_SERVICE_ACCOUNT = "GOOGLE_CHAT_SERVICE_ACCOUNT"
ENV_SERVICE_ACCOUNT_FILE = "GOOGLE_CHAT_SERVICE_ACCOUNT_FILE"
USE_ENV_FLAG = "__googlechatUseEnv"
AUTH_METHOD_FLAG = "__googlechatAuthMethod"


def _resolve_default_setup_account_id(params: dict) -> str | None:
    return resolve_default_google_chat_account_id(params.get("cfg"))


def _list_setup_account_ids(params: dict) -> list[str]:
    return list_google_chat_account_ids(params.get("cfg"))


def _build_runtime_setup_link(params: dict) -> str:
    account_id = params.get("accountId")
    return f"googlechat://accounts/{account_id or 'default'}/setup"


def _build_runtime_setup_view(params: dict) -> dict:
    account_id = params.get("accountId") or _resolve_default_setup_account_id(params)
    account = None
    if account_id:
        account = resolve_google_chat_account(
            cfg=params.get("cfg"),
            account_id=account_id,
        )

    if not account:
        return {
            "kind": "googlechat/setup",
            "accountId": account_id,
            "enabled": False,
            "configured": False,
            "reason": "account not found",
        }

    credential_source = normalize_lowercase_string_or_empty(account.config.get("credentialSource"))
    audience = normalize_lowercase_string_or_empty(account.config.get("audience"))
    audience_type = normalize_lowercase_string_or_empty(account.config.get("audienceType"))

    has_webhook_identity = bool(audience) and (
        (audience_type == "app-url" and bool(normalize_lowercase_string_or_empty(account.config.get("appPrincipal"))))
        or (audience_type == "project-number")
    )

    return {
        "kind": "googlechat/setup",
        "accountId": account.account_id,
        "enabled": account.enabled,
        "configured": account.enabled and credential_source != "none",
        "credentialSource": credential_source,
        "audienceType": audience_type,
        "audience": audience,
        "hasWebhookIdentity": has_webhook_identity,
        "webhookUrl": account.config.get("webhookUrl"),
    }


def _summarize_runtime_setup_view(view: dict) -> str:
    return f"Google Chat account {view.get('accountId', 'unknown')}: " + (
        "configured" if view.get("configured") else "not configured"
    )


google_chat_runtime_setup = {
    "resolveDefaultAccountId": _resolve_default_setup_account_id,
    "listAccountIds": _list_setup_account_ids,
    "buildLink": _build_runtime_setup_link,
    "buildView": _build_runtime_setup_view,
    "summarizeView": _summarize_runtime_setup_view,
}


def _create_service_account_text_input(params: dict) -> dict:
    return {
        "inputKey": params["inputKey"],
        "message": params["message"],
        "placeholder": params["placeholder"],
        "shouldPrompt": lambda p: (
            p["credentialValues"].get(USE_ENV_FLAG) != "1"
            and p["credentialValues"].get(AUTH_METHOD_FLAG) == params["authMethod"]
        ),
        "validate": lambda p: (
            None if normalize_stringified_optional_string(p.get("value")) else "Required"
        ),
        "normalizeValue": lambda p: normalize_stringified_optional_string(p.get("value")) or "",
        "applySet": lambda p: None,
    }


googlechat_setup_wizard = {
    "channel": channel,
    "status": create_standard_channel_setup_status({
        "channelLabel": "Google Chat",
        "configuredLabel": t("wizard.channels.statusConfigured"),
        "unconfiguredLabel": t("wizard.channels.statusNeedsServiceAccount"),
        "configuredHint": t("wizard.channels.statusConfigured"),
        "unconfiguredHint": t("wizard.channels.statusNeedsAuth"),
        "includeStatusLine": True,
        "resolveConfigured": lambda p: (
            resolve_google_chat_account(cfg=p["cfg"], account_id=p.get("accountId")).credential_source != "none"
        ),
    }),
    "introNote": {
        "title": t("wizard.googlechat.setupTitle"),
        "lines": [
            t("wizard.googlechat.setupServiceAccount"),
            t("wizard.googlechat.setupScopes"),
            t("wizard.googlechat.setupAudience"),
        ],
    },
    "prepare": lambda p: _prepare_setup_wizard(p),
    "credentials": [],
    "textInputs": [
        _create_service_account_text_input({
            "inputKey": "tokenFile",
            "message": t("wizard.googlechat.serviceAccountPath"),
            "placeholder": "/path/to/service-account.json",
            "authMethod": "file",
        }),
        _create_service_account_text_input({
            "inputKey": "token",
            "message": t("wizard.googlechat.serviceAccountJson"),
            "placeholder": '{"type":"service_account", ... }',
            "authMethod": "inline",
        }),
    ],
    "finalize": lambda p: _finalize_setup_wizard(p),
    "dmPolicy": {
        "label": "Google Chat",
        "channel": channel,
        "policyKey": "channels.googlechat.dm.policy",
        "allowFromKey": "channels.googlechat.dm.allowFrom",
    },
}


def _prepare_setup_wizard(params: dict) -> dict:
    account_id = params.get("accountId")
    credential_values = params.get("credentialValues", {})
    prompter = params.get("prompter")
    cfg = params.get("cfg")

    env_ready = (
        account_id == DEFAULT_ACCOUNT_ID
        and (bool(os.environ.get(ENV_SERVICE_ACCOUNT)) or bool(os.environ.get(ENV_SERVICE_ACCOUNT_FILE)))
    )
    if env_ready and prompter:
        use_env = prompter.confirm({
            "message": t("wizard.googlechat.useEnvPrompt"),
            "initialValue": True,
        })
        if use_env:
            return {
                "cfg": cfg,
                "credentialValues": {**credential_values, USE_ENV_FLAG: "1"},
            }

    method = "file"
    if prompter:
        method = prompter.select({
            "message": t("wizard.googlechat.authMethod"),
            "options": [
                {"value": "file", "label": t("wizard.googlechat.serviceAccountFile")},
                {"value": "inline", "label": t("wizard.googlechat.serviceAccountInline")},
            ],
            "initialValue": "file",
        })

    return {
        "credentialValues": {**credential_values, USE_ENV_FLAG: "0", AUTH_METHOD_FLAG: method},
    }


def _finalize_setup_wizard(params: dict) -> dict:
    cfg = params.get("cfg")
    account_id = params.get("accountId")
    prompter = params.get("prompter")
    account = resolve_google_chat_account(cfg=cfg, account_id=account_id)

    audience_type = "app-url"
    if prompter:
        audience_type = prompter.select({
            "message": t("wizard.googlechat.webhookAudienceType"),
            "options": [
                {"value": "app-url", "label": t("wizard.googlechat.appUrlRecommended")},
                {"value": "project-number", "label": t("wizard.googlechat.projectNumber")},
            ],
            "initialValue": (
                "project-number"
                if account.config.get("audienceType") == "project-number"
                else "app-url"
            ),
        })

    audience = account.config.get("audience", "")
    if prompter:
        audience = prompter.text({
            "message": (
                t("wizard.googlechat.projectNumber")
                if audience_type == "project-number"
                else t("wizard.googlechat.appUrl")
            ),
            "placeholder": (
                "1234567890"
                if audience_type == "project-number"
                else "https://your.host/googlechat"
            ),
            "initialValue": audience or None,
            "validate": lambda v: (
                None if normalize_stringified_optional_string(v) else t("common.required")
            ),
        })

    return {"cfg": cfg}


__all__ = ["google_chat_runtime_setup", "googlechat_setup_wizard"]