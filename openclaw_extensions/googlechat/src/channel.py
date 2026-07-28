from __future__ import annotations

import asyncio
import uuid
from typing import Any

from openclaw.plugin_sdk.channel_core import create_chat_channel_plugin
from openclaw.plugin_sdk.extension_shared import build_passive_probed_channel_status_summary
from openclaw.plugin_sdk.lazy_runtime import create_lazy_runtime_named_export
from openclaw.plugin_sdk.status_helpers import (
    create_computed_account_status_adapter,
    create_default_channel_runtime_state,
)
from openclaw.plugin_sdk.tool_send import extract_tool_send
from openclaw_extensions.googlechat.src.approval_native import (
    google_chat_approval_capability,
    should_suppress_local_google_chat_exec_approval_prompt,
)
from openclaw_extensions.googlechat.src.channel_base import (
    GOOGLECHAT_CHANNEL_ID,
    create_google_chat_plugin_base,
)
from openclaw_extensions.googlechat.src.channel_adapters import (
    googlechat_directory_adapter,
    googlechat_groups_adapter,
    googlechat_message_adapter,
    googlechat_outbound_adapter,
    googlechat_pairing_text_adapter,
    googlechat_security_adapter,
    googlechat_threading_adapter,
)
from openclaw_extensions.googlechat.src.channel_deps_runtime import (
    DEFAULT_ACCOUNT_ID,
    GoogleChatConfigSchema,
    ResolvedGoogleChatAccount,
    build_channel_config_schema,
    is_google_chat_space_target,
    is_google_chat_user_target,
    list_google_chat_account_ids,
    normalize_google_chat_target,
    resolve_google_chat_account,
)
from openclaw_extensions.googlechat.src.doctor import (
    collect_google_chat_mutable_allowlist_warnings,
)
from openclaw_extensions.googlechat.src.doctor_contract import (
    legacy_config_rules as GOOGLECHAT_LEGACY_CONFIG_RULES,
    normalize_compatibility_config as normalize_google_chat_compatibility_config,
)
from openclaw_extensions.googlechat.src.gateway import (
    start_google_chat_gateway_account,
)
from openclaw_extensions.googlechat.src.secret_contract import (
    collect_runtime_config_assignments,
    secret_target_registry_entries,
)

load_google_chat_channel_runtime = create_lazy_runtime_named_export(
    lambda: __import__(
        "openclaw_extensions.googlechat.src.channel_runtime",
        fromlist=["google_chat_channel_runtime"],
    ),
    "googleChatChannelRuntime",
)


async def _describe_message_tool(params: dict) -> dict | None:
    cfg = params.get("cfg")
    account_id = params.get("accountId")
    if account_id:
        accounts = [resolve_google_chat_account(cfg=cfg, account_id=account_id)]
        accounts = [
            a for a in accounts if a.enabled and a.credential_source != "none"
        ]
    else:
        accounts = [
            resolve_google_chat_account(cfg=cfg, account_id=aid)
            for aid in list_google_chat_account_ids(cfg)
        ]
        accounts = [
            a for a in accounts if a.enabled and a.credential_source != "none"
        ]
    if len(accounts) == 0:
        return None
    actions = {"send", "upload-file"}
    if any(a.config.get("actions", {}).get("reactions") is not False for a in accounts):
        actions.add("react")
        actions.add("reactions")
    return {"actions": list(actions)}


async def _handle_action(ctx: dict) -> Any:
    from openclaw_extensions.googlechat.src.actions import googlechat_message_actions

    if not googlechat_message_actions.get("handleAction"):
        raise RuntimeError("Google Chat actions are not available.")
    return await googlechat_message_actions["handleAction"](ctx)


googlechat_actions = {
    "describeMessageTool": _describe_message_tool,
    "extractToolSend": lambda params: extract_tool_send(params.get("args"), "sendMessage"),
    "handleAction": _handle_action,
}


async def _resolve_targets(params: dict) -> list[dict]:
    inputs = params.get("inputs", [])
    kind = params.get("kind")
    resolved = []
    for input_val in inputs:
        normalized = normalize_google_chat_target(input_val)
        if not normalized:
            resolved.append({"input": input_val, "resolved": False, "note": "empty target"})
            continue
        if kind == "user" and is_google_chat_user_target(normalized):
            resolved.append({"input": input_val, "resolved": True, "id": normalized})
            continue
        if kind == "group" and is_google_chat_space_target(normalized):
            resolved.append({"input": input_val, "resolved": True, "id": normalized})
            continue
        resolved.append({
            "input": input_val,
            "resolved": False,
            "note": "use spaces/{space} or users/{user}",
        })
    return resolved


googlechat_plugin = create_chat_channel_plugin({
    "base": {
        **create_google_chat_plugin_base({
            "configSchema": build_channel_config_schema(GoogleChatConfigSchema),
        }),
        "approvalCapability": google_chat_approval_capability,
        "secrets": {
            "secretTargetRegistryEntries": secret_target_registry_entries,
            "collectRuntimeConfigAssignments": collect_runtime_config_assignments,
        },
        "groups": googlechat_groups_adapter,
        "messaging": {
            "targetPrefixes": ["googlechat", "google-chat", "gchat"],
            "normalizeTarget": normalize_google_chat_target,
            "targetResolver": {
                "looksLikeId": lambda raw, normalized: (
                    is_google_chat_space_target(normalized or raw.strip())
                    or is_google_chat_user_target(normalized or raw.strip())
                ),
                "hint": "<spaces/{space}|users/{user}>",
            },
        },
        "directory": googlechat_directory_adapter,
        "message": googlechat_message_adapter,
        "resolver": {
            "resolveTargets": _resolve_targets,
        },
        "actions": googlechat_actions,
        "doctor": {
            "dmAllowFromMode": "nestedOnly",
            "groupModel": "route",
            "groupAllowFromFallbackToAllowFrom": False,
            "warnOnEmptyGroupSenderAllowlist": False,
            "legacyConfigRules": GOOGLECHAT_LEGACY_CONFIG_RULES,
            "normalizeCompatibilityConfig": normalize_google_chat_compatibility_config,
            "collectMutableAllowlistWarnings": collect_google_chat_mutable_allowlist_warnings,
        },
        "status": create_computed_account_status_adapter(
            default_runtime=create_default_channel_runtime_state(DEFAULT_ACCOUNT_ID),
            collect_status_issues=_collect_status_issues,
            build_channel_summary=lambda snapshot: build_passive_probed_channel_status_summary(
                snapshot,
                credential_source=snapshot.get("credentialSource", "none"),
                audience_type=snapshot.get("audienceType"),
                audience=snapshot.get("audience"),
                webhook_path=snapshot.get("webhookPath"),
                webhook_url=snapshot.get("webhookUrl"),
            ),
            probe_account=lambda account: (
                load_google_chat_channel_runtime().probeGoogleChat(account)
            ),
            resolve_account_snapshot=_resolve_account_snapshot,
        ),
        "gateway": {
            "startAccount": start_google_chat_gateway_account,
        },
    },
    "pairing": {
        "text": googlechat_pairing_text_adapter,
    },
    "security": googlechat_security_adapter,
    "threading": googlechat_threading_adapter,
    "outbound": {
        **googlechat_outbound_adapter,
        "base": {
            **googlechat_outbound_adapter.get("base", {}),
            "shouldSuppressLocalPayloadPrompt": lambda params: (
                should_suppress_local_google_chat_exec_approval_prompt(
                    cfg=params.get("cfg"),
                    account_id=params.get("accountId"),
                    payload=params.get("payload"),
                    hint=params.get("hint"),
                )
            ),
        },
    },
})


def _collect_status_issues(accounts: list) -> list:
    issues = []
    for entry in accounts:
        account_id = entry.get("accountId", DEFAULT_ACCOUNT_ID)
        enabled = entry.get("enabled", True)
        configured = entry.get("configured", False)
        if not enabled or not configured:
            continue
        if not entry.get("audience"):
            issues.append({
                "channel": GOOGLECHAT_CHANNEL_ID,
                "accountId": account_id,
                "kind": "config",
                "message": "Google Chat audience is missing (set channels.googlechat.audience).",
                "fix": "Set channels.googlechat.audienceType and channels.googlechat.audience.",
            })
        if not entry.get("audienceType"):
            issues.append({
                "channel": GOOGLECHAT_CHANNEL_ID,
                "accountId": account_id,
                "kind": "config",
                "message": "Google Chat audienceType is missing (app-url or project-number).",
                "fix": "Set channels.googlechat.audienceType and channels.googlechat.audience.",
            })
    return issues


def _resolve_account_snapshot(account: ResolvedGoogleChatAccount) -> dict:
    return {
        "accountId": account.account_id,
        "name": account.name,
        "enabled": account.enabled,
        "configured": account.credential_source != "none",
        "extra": {
            "credentialSource": account.credential_source,
            "audienceType": account.config.get("audienceType"),
            "audience": account.config.get("audience"),
            "webhookPath": account.config.get("webhookPath"),
            "webhookUrl": account.config.get("webhookUrl"),
            "dmPolicy": (account.config.get("dm") or {}).get("policy", "pairing"),
        },
    }


__all__ = ["googlechat_plugin", "googlechat_actions"]