from __future__ import annotations

from openclaw.plugin_sdk.approval_delivery_runtime import (
    create_approver_restricted_native_approval_capability,
)
from openclaw.plugin_sdk.approval_handler_adapter_runtime import (
    create_lazy_channel_approval_native_runtime_adapter,
)
from openclaw.plugin_sdk.approval_native_runtime import (
    create_channel_approver_dm_target_resolver,
    create_channel_native_origin_target_resolver,
    create_native_approval_channel_route_gates,
    should_suppress_local_native_exec_approval_prompt,
)
from openclaw.plugin_sdk.string_coerce_runtime import (
    normalize_lowercase_string_or_empty,
    normalize_optional_string,
)
from openclaw_extensions.googlechat.src.accounts import (
    list_google_chat_account_ids,
    resolve_default_google_chat_account_id,
    resolve_google_chat_account,
)
from openclaw_extensions.googlechat.src.approval_auth import (
    get_google_chat_approval_approvers,
    google_chat_approval_auth,
    normalize_google_chat_approver_id,
)
from openclaw_extensions.googlechat.src.targets import (
    is_google_chat_space_target,
    normalize_google_chat_target,
)

DEFAULT_APPROVAL_FORWARDING_MODE = "session"


def _is_google_chat_account_configured(params: dict) -> bool:
    account = resolve_google_chat_account(
        cfg=params.get("cfg"),
        account_id=params.get("accountId"),
    )
    return account.enabled and account.credential_source != "none"


def _has_google_chat_webhook_approval_auth_config(params: dict) -> bool:
    account = resolve_google_chat_account(
        cfg=params.get("cfg"),
        account_id=params.get("accountId"),
    )
    audience = normalize_optional_string(account.config.get("audience"))
    if not audience:
        return False
    if account.config.get("audienceType") == "project-number":
        return True
    return account.config.get("audienceType") == "app-url"


def _is_google_chat_approval_transport_enabled(params: dict) -> bool:
    return _is_google_chat_account_configured(params) and _has_google_chat_webhook_approval_auth_config(params)


def _normalize_google_chat_forward_target(target: dict) -> dict | None:
    if normalize_lowercase_string_or_empty(target.get("channel")) != "googlechat":
        return None
    to = normalize_google_chat_target(target.get("to", ""))
    if not to:
        return None
    return {
        "to": to,
        "accountId": normalize_optional_string(target.get("accountId")),
        "threadId": target.get("threadId"),
    }


def _resolve_turn_source_google_chat_origin_target(request: dict) -> dict | None:
    turn_source_channel = normalize_lowercase_string_or_empty(
        request.get("request", {}).get("turnSourceChannel")
    )
    if turn_source_channel != "googlechat":
        return None
    target = normalize_google_chat_target(
        request.get("request", {}).get("turnSourceTo", "")
    )
    if not target or not is_google_chat_space_target(target):
        return None
    return {
        "to": target,
        "accountId": normalize_optional_string(
            request.get("request", {}).get("turnSourceAccountId")
        ),
        "threadId": request.get("request", {}).get("turnSourceThreadId"),
    }


google_chat_approval_route_gates = create_native_approval_channel_route_gates({
    "channel": "googlechat",
    "defaultForwardingMode": DEFAULT_APPROVAL_FORWARDING_MODE,
    "isTransportEnabled": _is_google_chat_approval_transport_enabled,
    "listAccountIds": list_google_chat_account_ids,
    "resolveDefaultAccountId": resolve_default_google_chat_account_id,
    "normalizeForwardTarget": _normalize_google_chat_forward_target,
    "resolveTurnSourceTarget": _resolve_turn_source_google_chat_origin_target,
})


def is_google_chat_native_approval_client_enabled(params: dict) -> bool:
    return (
        google_chat_approval_route_gates.can_any_approval_potentially_route_to_channel({
            **params,
            "nativeSessionOnly": True,
        })
        and len(get_google_chat_approval_approvers(params)) > 0
    )


def _resolve_session_google_chat_origin_target(session_target: dict) -> dict | None:
    target = normalize_google_chat_target(session_target.get("to", ""))
    if target and is_google_chat_space_target(target):
        return {"to": target, "threadId": session_target.get("threadId")}
    return None


def should_handle_google_chat_native_approval_request(params: dict) -> bool:
    request = params.get("request", {})
    return (
        google_chat_approval_route_gates.should_handle_approval_request(params)
        and len(get_google_chat_approval_approvers(params)) > 0
        and bool(_resolve_turn_source_google_chat_origin_target(request))
    )


def should_suppress_local_google_chat_exec_approval_prompt(params: dict) -> bool:
    from openclaw.plugin_sdk.approval_native_runtime import should_suppress_local_native_exec_approval_prompt

    return should_suppress_local_native_exec_approval_prompt({
        **params,
        "isNativeDeliveryEnabled": is_google_chat_native_approval_client_enabled,
    })


_resolve_google_chat_origin_target = create_channel_native_origin_target_resolver({
    "channel": "googlechat",
    "shouldHandleRequest": should_handle_google_chat_native_approval_request,
    "resolveTurnSourceTarget": _resolve_turn_source_google_chat_origin_target,
    "resolveSessionTarget": _resolve_session_google_chat_origin_target,
})

_resolve_google_chat_approver_dm_targets = create_channel_approver_dm_target_resolver({
    "shouldHandleRequest": should_handle_google_chat_native_approval_request,
    "resolveApprovers": get_google_chat_approval_approvers,
    "mapApprover": lambda approver, params: (
        {
            "to": normalize_google_chat_approver_id(approver),
            "accountId": normalize_optional_string(params.get("accountId")),
        }
        if normalize_google_chat_approver_id(approver)
        else None
    ),
})

google_chat_approval_capability = create_approver_restricted_native_approval_capability({
    "channel": "googlechat",
    "channelLabel": "Google Chat",
    "describeExecApprovalSetup": lambda params: (
        f'Approve it from the Web UI or terminal UI for now. Google Chat supports native approvals for this account when the webhook and service account are configured. '
        f'Configure `channels.googlechat.dm.allowFrom` or `channels.googlechat.defaultTo` with numeric `users/{{id}}` approvers.'
    ),
    "listAccountIds": list_google_chat_account_ids,
    "hasApprovers": lambda params: (
        len(get_google_chat_approval_approvers(params)) > 0
    ),
    "isExecAuthorizedSender": lambda params: (
        google_chat_approval_auth.authorize_actor_action({
            "cfg": params.get("cfg"),
            "accountId": params.get("accountId"),
            "senderId": params.get("senderId"),
            "action": "approve",
            "approvalKind": "exec",
        }).get("authorized", False)
    ),
    "isPluginAuthorizedSender": lambda params: (
        google_chat_approval_auth.authorize_actor_action({
            "cfg": params.get("cfg"),
            "accountId": params.get("accountId"),
            "senderId": params.get("senderId"),
            "action": "approve",
            "approvalKind": "plugin",
        }).get("authorized", False)
    ),
    "isNativeDeliveryEnabled": is_google_chat_native_approval_client_enabled,
    "resolveNativeDeliveryMode": lambda: "channel",
    "requireMatchingTurnSourceChannel": True,
    "resolveSuppressionAccountId": lambda params: (
        normalize_optional_string(params.get("target", {}).get("accountId"))
        or normalize_optional_string(
            params.get("request", {}).get("turnSourceAccountId")
        )
    ),
    "resolveOriginTarget": _resolve_google_chat_origin_target,
    "resolveApproverDmTargets": _resolve_google_chat_approver_dm_targets,
    "nativeRuntime": create_lazy_channel_approval_native_runtime_adapter({
        "eventKinds": ["exec", "plugin"],
        "isConfigured": lambda params: is_google_chat_native_approval_client_enabled(params),
        "shouldHandle": lambda params: should_handle_google_chat_native_approval_request(params),
        "load": lambda: __import__(
            "openclaw_extensions.googlechat.src.approval_handler_runtime",
            fromlist=["google_chat_approval_native_runtime"],
        ).google_chat_approval_native_runtime,
    }),
})

__all__ = [
    "google_chat_approval_capability",
    "is_google_chat_native_approval_client_enabled",
    "should_handle_google_chat_native_approval_request",
    "should_suppress_local_google_chat_exec_approval_prompt",
]