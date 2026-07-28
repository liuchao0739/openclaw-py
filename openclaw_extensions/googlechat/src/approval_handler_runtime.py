from __future__ import annotations

import time
from typing import Any

from openclaw.plugin_sdk.approval_handler_runtime import (
    create_channel_approval_native_runtime_adapter,
)
from openclaw.plugin_sdk.approval_native_runtime import (
    build_channel_approval_native_target_key,
)
from openclaw.plugin_sdk.runtime_env import create_subsystem_logger
from openclaw.plugin_sdk.string_coerce_runtime import normalize_optional_string
from openclaw_extensions.googlechat.src.accounts import (
    ResolvedGoogleChatAccount,
    resolve_google_chat_account,
)
from openclaw_extensions.googlechat.src.api import (
    send_google_chat_message,
    update_google_chat_message,
)
from openclaw_extensions.googlechat.src.approval_card_actions import (
    GOOGLECHAT_APPROVAL_ACTION,
    build_google_chat_approval_action_parameters,
    create_google_chat_approval_token,
    register_google_chat_approval_card_binding,
    unregister_google_chat_approval_card_bindings,
    unregister_google_chat_manual_approval_followup_suppression,
)
from openclaw_extensions.googlechat.src.approval_native import (
    is_google_chat_native_approval_client_enabled,
    should_handle_google_chat_native_approval_request,
)
from openclaw_extensions.googlechat.src.targets import resolve_google_chat_outbound_space
from openclaw_extensions.googlechat.src.types import GoogleChatCardV2

log = create_subsystem_logger("googlechat/approvals")
GOOGLECHAT_APPROVAL_CARD_ID = "openclaw-approval"
MAX_TEXT_PARAGRAPH_CHARS = 1800


def _escape_google_chat_text(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _truncate_text(text: str, max_chars: int = MAX_TEXT_PARAGRAPH_CHARS) -> str:
    return text if len(text) <= max_chars else text[: max_chars - 3] + "..."


def _build_metadata_text(metadata: list[dict]) -> str:
    return "<br>".join(
        f"<b>{_escape_google_chat_text(item['label'])}:</b> {_escape_google_chat_text(item['value'])}"
        for item in metadata
    )


def _format_decision(decision: str) -> str:
    if decision == "allow-once":
        return "Allowed once"
    if decision == "allow-always":
        return "Allowed always"
    return "Denied"


def _build_main_text_widget(text: str) -> dict:
    return {"textParagraph": {"text": _escape_google_chat_text(_truncate_text(text))}}


def _build_html_text_widget(text: str) -> dict:
    return {"textParagraph": {"text": _truncate_text(text)}}


def _build_exec_pending_sections(view: dict) -> list:
    if view.get("approvalKind") != "exec":
        return []
    sections = [{"header": "Command", "widgets": [_build_main_text_widget(view.get("commandText", ""))]}]
    preview = view.get("commandPreview")
    if preview and preview != view.get("commandText"):
        sections.append({"header": "Preview", "widgets": [_build_main_text_widget(preview)]})
    return sections


def _build_plugin_pending_sections(view: dict) -> list:
    if view.get("approvalKind") != "plugin":
        return []
    title = _escape_google_chat_text(view.get("title", ""))
    description = view.get("description")
    html = f"<b>{title}</b>"
    if description:
        html += f"<br>{_escape_google_chat_text(description)}"
    return [{"header": "Request", "widgets": [_build_html_text_widget(html)]}]


def _build_metadata_section(view: dict) -> list:
    metadata = [{"label": "Approval ID", "value": view.get("approvalId", "")}] + view.get("metadata", [])
    if len(metadata) == 0:
        return []
    return [{"header": "Details", "widgets": [_build_html_text_widget(_build_metadata_text(metadata))]}]


def _build_action_section(params: dict) -> dict:
    action_function = params["actionFunction"]
    view = params["view"]
    action_tokens = [
        {"token": create_google_chat_approval_token(), "decision": action["decision"]}
        for action in view.get("actions", [])
    ]
    buttons = []
    for i, action in enumerate(view.get("actions", [])):
        token = action_tokens[i]
        buttons.append({
            "text": action["label"],
            "onClick": {
                "action": {
                    "function": action_function,
                    "parameters": build_google_chat_approval_action_parameters(token["token"]),
                    "loadIndicator": "SPINNER",
                },
            },
        })
    return {
        "actionTokens": action_tokens,
        "section": {"widgets": [{"buttonList": {"buttons": buttons}}]},
    }


def _build_pending_payload(params: dict) -> dict:
    action_function = params["actionFunction"]
    now_ms = params["nowMs"]
    view = params["view"]
    action_section = _build_action_section({"actionFunction": action_function, "view": view})
    approval_kind = view.get("approvalKind", "exec")
    title = "Plugin Approval Required" if approval_kind == "plugin" else "Exec Approval Required"
    remaining = max(0, int((view.get("expiresAtMs", 0) - now_ms) / 1000))
    subtitle = f"Expires in {remaining}s"
    card = {
        "cardId": GOOGLECHAT_APPROVAL_CARD_ID,
        "card": {
            "header": {"title": title, "subtitle": subtitle},
            "sections": (
                _build_exec_pending_sections(view)
                + _build_plugin_pending_sections(view)
                + _build_metadata_section(view)
                + [action_section["section"]]
            ),
        },
    }
    return {
        "approvalId": view.get("approvalId"),
        "approvalKind": approval_kind,
        "expiresAtMs": view.get("expiresAtMs"),
        "cardsV2": [card],
        "actionTokens": action_section["actionTokens"],
        "allowedDecisions": [a["decision"] for a in view.get("actions", [])],
    }


def _resolve_approval_action_function(params: dict) -> str:
    account = _resolve_handler_account(params)
    audience = normalize_optional_string(account.config.get("audience")) if account else None
    app_principal = normalize_optional_string(account.config.get("appPrincipal")) if account else None
    if account and account.config.get("audienceType") == "app-url" and audience and app_principal:
        return audience
    return GOOGLECHAT_APPROVAL_ACTION


def _resolve_handler_account(params: dict) -> ResolvedGoogleChatAccount | None:
    context = params.get("context", {})
    account = context.get("account") if context else None
    if account:
        return account
    resolved = resolve_google_chat_account(
        cfg=params.get("cfg"),
        account_id=params.get("accountId"),
    )
    if not resolved.enabled or resolved.credential_source == "none":
        return None
    return resolved


def _build_resolved_payload(view: dict) -> dict:
    resolved_by = normalize_optional_string(view.get("resolvedBy"))
    approval_kind = view.get("approvalKind", "exec")
    title = f"{'Plugin' if approval_kind == 'plugin' else 'Exec'} Approval: {_format_decision(view.get('decision', ''))}"
    subtitle = f"Resolved by {resolved_by}" if resolved_by else "Resolved"
    card = {
        "cardId": GOOGLECHAT_APPROVAL_CARD_ID,
        "card": {"header": {"title": title, "subtitle": subtitle}, "sections": _build_metadata_section(view)},
    }
    return {"cardsV2": [card]}


def _build_expired_payload(view: dict) -> dict:
    approval_kind = view.get("approvalKind", "exec")
    title = f"{'Plugin' if approval_kind == 'plugin' else 'Exec'} Approval Expired"
    card = {
        "cardId": GOOGLECHAT_APPROVAL_CARD_ID,
        "card": {
            "header": {"title": title, "subtitle": "This approval request expired before it was resolved."},
            "sections": _build_metadata_section(view),
        },
    }
    return {"cardsV2": [card]}


google_chat_approval_native_runtime = create_channel_approval_native_runtime_adapter({
    "eventKinds": ["exec", "plugin"],
    "availability": {
        "isConfigured": lambda params: is_google_chat_native_approval_client_enabled(params),
        "shouldHandle": lambda params: should_handle_google_chat_native_approval_request(params),
    },
    "presentation": {
        "buildPendingPayload": lambda params: _build_pending_payload({
            "actionFunction": _resolve_approval_action_function(params),
            "nowMs": params["nowMs"],
            "view": params["view"],
        }),
        "buildResolvedResult": lambda params: {
            "kind": "update",
            "payload": _build_resolved_payload(params["view"]),
        },
        "buildExpiredResult": lambda params: {
            "kind": "update",
            "payload": _build_expired_payload(params["view"]),
        },
    },
    "transport": {
        "prepareTarget": lambda params: {
            "dedupeKey": build_channel_approval_native_target_key(params["plannedTarget"]["target"]),
            "target": {
                "to": params["plannedTarget"]["target"]["to"],
                "threadName": (
                    str(params["plannedTarget"]["target"]["threadId"])
                    if params["plannedTarget"]["target"].get("threadId") is not None
                    else None
                ),
            },
        },
        "deliverPending": lambda params: _deliver_pending(params),
        "updateEntry": lambda params: _update_entry(params),
    },
    "interactions": {
        "bindPending": lambda params: _bind_pending(params),
        "unbindPending": lambda params: _unbind_pending(params),
        "cancelDelivered": lambda params: _cancel_delivered(params),
    },
    "observe": {
        "onDeliveryError": lambda params: (
            log.error(f"googlechat approvals: failed to send request {params['request'].id}: {params['error']}")
        ),
    },
})


async def _deliver_pending(params: dict) -> dict | None:
    account = _resolve_handler_account(params)
    if not account:
        return None
    space_name = await resolve_google_chat_outbound_space({
        "account": account,
        "target": params["preparedTarget"]["target"]["to"],
    })
    pending_payload = params["pendingPayload"]
    _register_manual_approval_followup_suppression({
        "approvalId": pending_payload["approvalId"],
        "approvalKind": pending_payload["approvalKind"],
        "allowedDecisions": pending_payload["allowedDecisions"],
        "expiresAtMs": pending_payload["expiresAtMs"],
    })
    try:
        sent = await send_google_chat_message({
            "account": account,
            "space": space_name,
            "cardsV2": pending_payload["cardsV2"],
            "thread": params["preparedTarget"]["target"].get("threadName"),
        })
    except Exception as error:
        unregister_google_chat_manual_approval_followup_suppression(
            pending_payload["approvalId"]
        )
        raise error
    if not sent or not sent.get("messageName"):
        unregister_google_chat_manual_approval_followup_suppression(
            pending_payload["approvalId"]
        )
        return None
    result = {
        "accountId": account.account_id,
        "spaceName": space_name,
        "messageName": sent["messageName"],
        "actionTokens": pending_payload["actionTokens"],
    }
    if params["preparedTarget"]["target"].get("threadName"):
        result["threadName"] = params["preparedTarget"]["target"]["threadName"]
    return result


async def _update_entry(params: dict) -> None:
    account = _resolve_handler_account(params)
    if not account:
        return
    await update_google_chat_message({
        "account": account,
        "messageName": params["entry"]["messageName"],
        "cardsV2": params["payload"]["cardsV2"],
    })


def _bind_pending(params: dict) -> list | None:
    tokens = []
    for action_token in params["entry"]["actionTokens"]:
        ok = register_google_chat_approval_card_binding({
            "token": action_token["token"],
            "accountId": params["accountId"],
            "approvalId": params["request"]["id"],
            "approvalKind": params["approvalKind"],
            "decision": action_token["decision"],
            "allowedDecisions": params["pendingPayload"]["allowedDecisions"],
            "spaceName": params["entry"]["spaceName"],
            "messageName": params["entry"]["messageName"],
            "threadName": params["entry"].get("threadName"),
            "expiresAtMs": params["view"]["expiresAtMs"],
        })
        if ok:
            tokens.append(action_token["token"])
    return tokens if len(tokens) > 0 else None


def _unbind_pending(params: dict) -> None:
    unregister_google_chat_approval_card_bindings(params["binding"])


def _cancel_delivered(params: dict) -> None:
    unregister_google_chat_approval_card_bindings(
        [t["token"] for t in params["entry"]["actionTokens"]]
    )


def _register_manual_approval_followup_suppression(suppression: dict) -> None:
    from openclaw_extensions.googlechat.src.approval_card_actions import (
        register_google_chat_manual_approval_followup_suppression,
    )
    register_google_chat_manual_approval_followup_suppression(suppression)


__all__ = ["google_chat_approval_native_runtime"]