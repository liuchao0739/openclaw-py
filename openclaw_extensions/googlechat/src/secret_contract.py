from __future__ import annotations

from typing import Any

from openclaw.plugin_sdk.channel_secret_basic_runtime import (
    get_channel_surface,
    has_own_property,
    push_assignment,
    push_inactive_surface_warning,
    push_warning,
    resolve_channel_account_surface,
)
from openclaw.plugin_sdk.secret_ref_runtime import coerce_secret_ref

secret_target_registry_entries: list[dict] = [
    {
        "id": "channels.googlechat.accounts.*.serviceAccount",
        "targetType": "channels.googlechat.serviceAccount",
        "targetTypeAliases": ["channels.googlechat.accounts.*.serviceAccount"],
        "configFile": "openclaw.json",
        "pathPattern": "channels.googlechat.accounts.*.serviceAccount",
        "refPathPattern": "channels.googlechat.accounts.*.serviceAccountRef",
        "secretShape": "sibling_ref",
        "expectedResolvedValue": "string-or-object",
        "includeInPlan": True,
        "includeInConfigure": True,
        "includeInAudit": True,
        "accountIdPathSegmentIndex": 3,
    },
    {
        "id": "channels.googlechat.serviceAccount",
        "targetType": "channels.googlechat.serviceAccount",
        "configFile": "openclaw.json",
        "pathPattern": "channels.googlechat.serviceAccount",
        "refPathPattern": "channels.googlechat.serviceAccountRef",
        "secretShape": "sibling_ref",
        "expectedResolvedValue": "string-or-object",
        "includeInPlan": True,
        "includeInConfigure": True,
        "includeInAudit": True,
    },
]


def _resolve_secret_input_ref(params: dict) -> dict:
    explicit_ref = coerce_secret_ref(params.get("refValue"), params.get("defaults"))
    inline_ref = None if explicit_ref else coerce_secret_ref(params.get("value"), params.get("defaults"))
    return {
        "explicitRef": explicit_ref,
        "inlineRef": inline_ref,
        "ref": explicit_ref or inline_ref,
    }


def _collect_google_chat_account_assignment(params: dict) -> None:
    target = params["target"]
    resolved = _resolve_secret_input_ref({
        "value": target.get("serviceAccount"),
        "refValue": target.get("serviceAccountRef"),
        "defaults": params.get("defaults"),
    })
    ref = resolved.get("ref")
    if not ref:
        return
    if params.get("active") is False:
        push_inactive_surface_warning({
            "context": params["context"],
            "path": f'{params["path"]}.serviceAccount',
            "details": params.get("inactiveReason"),
        })
        return
    explicit_ref = resolved.get("explicitRef")
    if (
        explicit_ref
        and target.get("serviceAccount") is not None
        and not coerce_secret_ref(target.get("serviceAccount"), params.get("defaults"))
    ):
        push_warning(params["context"], {
            "code": "SECRETS_REF_OVERRIDES_PLAINTEXT",
            "path": params["path"],
            "message": f'{params["path"]}: serviceAccountRef is set; runtime will ignore plaintext serviceAccount.',
        })
    push_assignment(params["context"], {
        "ref": ref,
        "path": f'{params["path"]}.serviceAccount',
        "expected": "string-or-object",
        "apply": lambda value: target.__setitem__("serviceAccount", value),
    })


def collect_runtime_config_assignments(params: dict) -> None:
    config = params.get("config", {})
    resolved = get_channel_surface(config, "googlechat")
    if not resolved:
        return
    google_chat = resolved["channel"]
    surface = resolve_channel_account_surface(google_chat)
    top_level_service_account_active = (
        False
        if not surface["channelEnabled"]
        else (
            True
            if not surface["hasExplicitAccounts"]
            else any(
                account_entry["enabled"]
                and not has_own_property(account_entry["account"], "serviceAccount")
                and not has_own_property(account_entry["account"], "serviceAccountRef")
                for account_entry in surface["accounts"]
            )
        )
    )
    _collect_google_chat_account_assignment({
        "target": google_chat,
        "path": "channels.googlechat",
        "defaults": params.get("defaults"),
        "context": params["context"],
        "active": top_level_service_account_active,
        "inactiveReason": "no enabled account inherits this top-level Google Chat serviceAccount.",
    })
    if not surface["hasExplicitAccounts"]:
        return
    for account_entry in surface["accounts"]:
        account = account_entry["account"]
        if not has_own_property(account, "serviceAccount") and not has_own_property(account, "serviceAccountRef"):
            continue
        _collect_google_chat_account_assignment({
            "target": account,
            "path": f'channels.googlechat.accounts.{account_entry["accountId"]}',
            "defaults": params.get("defaults"),
            "context": params["context"],
            "active": account_entry["enabled"],
            "inactiveReason": "Google Chat account is disabled.",
        })


channel_secrets = {
    "secretTargetRegistryEntries": secret_target_registry_entries,
    "collectRuntimeConfigAssignments": collect_runtime_config_assignments,
}

__all__ = [
    "channel_secrets",
    "collect_runtime_config_assignments",
    "secret_target_registry_entries",
]