from __future__ import annotations

import re
import time
import uuid
from typing import Any

from openclaw.plugin_sdk.string_coerce_runtime import normalize_optional_string
from openclaw_extensions.googlechat.src.types import GoogleChatActionParameter, GoogleChatEvent

GOOGLECHAT_APPROVAL_ACTION = "openclaw.approval"
GOOGLECHAT_APPROVAL_ACTION_PARAM = "openclaw_action"
GOOGLECHAT_APPROVAL_TOKEN_PARAM = "token"
GOOGLECHAT_APPROVAL_ACTION_VALUE = "approval"

MANUAL_EXEC_APPROVAL_COMMAND_RE = re.compile(
    r"(?:^|[\s`])/approve[ \t]+([^ \t\r\n`|]+)[ \t]+(allow-once|allow-always|deny)(?=$|[\s`|.,;:!?])",
    re.IGNORECASE,
)

approval_card_bindings: dict[str, dict] = {}
approval_card_resolving_tokens: set[str] = set()
manual_approval_followup_suppressions: dict[str, dict] = {}


def create_google_chat_approval_token() -> str:
    return uuid.urlsafe_base64().decode().rstrip("=")


def build_google_chat_approval_action_parameters(token: str) -> list[GoogleChatActionParameter]:
    return [
        {"key": GOOGLECHAT_APPROVAL_ACTION_PARAM, "value": GOOGLECHAT_APPROVAL_ACTION_VALUE},
        {"key": GOOGLECHAT_APPROVAL_TOKEN_PARAM, "value": token},
    ]


def _collect_event_parameters(event: GoogleChatEvent) -> dict[str, str]:
    params: dict[str, str] = {}
    for key, value in (event.get("common") or {}).get("parameters", {}).items():
        if isinstance(value, str):
            params[key] = value
    for key, value in (event.get("commonEventObject") or {}).get("parameters", {}).items():
        if isinstance(value, str):
            params[key] = value
    for item in (event.get("action") or {}).get("parameters", []):
        if isinstance(item.get("key"), str) and isinstance(item.get("value"), str):
            params[item["key"]] = item["value"]
    return params


def read_google_chat_approval_action_token(event: GoogleChatEvent) -> str | None:
    params = _collect_event_parameters(event)
    if params.get(GOOGLECHAT_APPROVAL_ACTION_PARAM) != GOOGLECHAT_APPROVAL_ACTION_VALUE:
        return None
    action_name = (
        normalize_optional_string((event.get("action") or {}).get("actionMethodName"))
        or normalize_optional_string((event.get("common") or {}).get("invokedFunction"))
        or normalize_optional_string((event.get("commonEventObject") or {}).get("invokedFunction"))
    )
    if action_name and action_name != GOOGLECHAT_APPROVAL_ACTION and not action_name.startswith("https://"):
        return None
    return normalize_optional_string(params.get(GOOGLECHAT_APPROVAL_TOKEN_PARAM))


def register_google_chat_approval_card_binding(binding: dict) -> bool:
    if binding.get("expiresAtMs", 0) <= time.time() * 1000:
        return False
    approval_card_bindings[binding["token"]] = binding
    _register_manual_approval_followup_suppression({
        "approvalId": binding["approvalId"],
        "approvalKind": binding["approvalKind"],
        "allowedDecisions": binding["allowedDecisions"],
        "expiresAtMs": binding["expiresAtMs"],
    })
    return True


def get_google_chat_approval_card_binding(token: str) -> dict | None:
    binding = approval_card_bindings.get(token)
    if not binding:
        return None
    if binding.get("expiresAtMs", 0) <= time.time() * 1000:
        approval_card_bindings.pop(token, None)
        return None
    return binding


def _normalize_approval_ref(value: str) -> str | None:
    normalized = value.strip().lower()
    return normalized if normalized else None


def _manual_approval_followup_suppression_key(approval_id: str) -> str | None:
    return _normalize_approval_ref(approval_id)


def _register_manual_approval_followup_suppression(suppression: dict) -> bool:
    if suppression.get("expiresAtMs", 0) <= time.time() * 1000:
        return False
    key = _manual_approval_followup_suppression_key(suppression["approvalId"])
    if not key:
        return False
    manual_approval_followup_suppressions[key] = suppression
    return True


def unregister_google_chat_manual_approval_followup_suppression(approval_id: str) -> None:
    key = _manual_approval_followup_suppression_key(approval_id)
    if key:
        manual_approval_followup_suppressions.pop(key, None)


def _approval_ref_matches(binding_approval_id: str, approval_ref: str) -> bool:
    normalized_binding_id = _normalize_approval_ref(binding_approval_id)
    normalized_ref = _normalize_approval_ref(approval_ref)
    if not normalized_binding_id or not normalized_ref:
        return False
    return normalized_ref == normalized_binding_id or (
        len(normalized_ref) >= 8 and normalized_binding_id.startswith(normalized_ref)
    )


def _prune_expired_google_chat_approval_card_bindings(now_ms: float) -> None:
    expired_tokens = [t for t, b in approval_card_bindings.items() if b.get("expiresAtMs", 0) <= now_ms]
    for token in expired_tokens:
        approval_card_bindings.pop(token, None)
        approval_card_resolving_tokens.discard(token)

    expired_keys = [k for k, s in manual_approval_followup_suppressions.items() if s.get("expiresAtMs", 0) <= now_ms]
    for key in expired_keys:
        manual_approval_followup_suppressions.pop(key, None)


def _has_active_google_chat_exec_approval_card_for_manual_command(params: dict) -> bool:
    _prune_expired_google_chat_approval_card_bindings(params["nowMs"])
    for binding in approval_card_bindings.values():
        if (
            binding.get("approvalKind") == "exec"
            and params["decision"] in binding.get("allowedDecisions", [])
            and _approval_ref_matches(binding.get("approvalId", ""), params["approvalRef"])
        ):
            return True
    for suppression in manual_approval_followup_suppressions.values():
        if (
            suppression.get("approvalKind") == "exec"
            and params["decision"] in suppression.get("allowedDecisions", [])
            and _approval_ref_matches(suppression.get("approvalId", ""), params["approvalRef"])
        ):
            return True
    return False


def should_suppress_google_chat_manual_exec_approval_followup_text(
    text: str,
    now_ms: float | None = None,
) -> bool:
    if now_ms is None:
        now_ms = time.time() * 1000
    for match in MANUAL_EXEC_APPROVAL_COMMAND_RE.finditer(text):
        approval_ref = match.group(1)
        decision = match.group(2)
        if approval_ref and decision and _has_active_google_chat_exec_approval_card_for_manual_command({
            "approvalRef": approval_ref,
            "decision": decision.lower(),
            "nowMs": now_ms,
        }):
            return True
    return False


def _has_structured_payload_part(payload: dict) -> bool:
    return bool(
        (payload.get("mediaUrl") or "").strip()
        or any(url.strip() for url in payload.get("mediaUrls", []) if url)
        or payload.get("presentation")
        or payload.get("interactive")
        or payload.get("btw")
        or payload.get("spokenText")
        or payload.get("ttsSupplement")
    )


def should_suppress_google_chat_manual_exec_approval_followup_payload(
    payload: dict,
    now_ms: float | None = None,
) -> bool:
    if now_ms is None:
        now_ms = time.time() * 1000
    text = (payload.get("text") or "").strip()
    if not text or _has_structured_payload_part(payload):
        return False
    return should_suppress_google_chat_manual_exec_approval_followup_text(text, now_ms)


def claim_google_chat_approval_card_binding(token: str) -> dict:
    binding = get_google_chat_approval_card_binding(token)
    if not binding:
        return {"kind": "missing"}
    if token in approval_card_resolving_tokens:
        return {"kind": "in-flight"}
    approval_card_resolving_tokens.add(token)
    return {"kind": "claimed", "binding": binding}


def complete_google_chat_approval_card_binding(token: str) -> None:
    binding = approval_card_bindings.get(token)
    approval_card_resolving_tokens.discard(token)
    approval_card_bindings.pop(token, None)
    if binding:
        unregister_google_chat_manual_approval_followup_suppression(binding["approvalId"])


def release_google_chat_approval_card_binding(token: str) -> None:
    approval_card_resolving_tokens.discard(token)


def unregister_google_chat_approval_card_bindings(tokens: list[str]) -> None:
    for token in tokens:
        binding = approval_card_bindings.get(token)
        approval_card_bindings.pop(token, None)
        approval_card_resolving_tokens.discard(token)
        if binding:
            unregister_google_chat_manual_approval_followup_suppression(binding["approvalId"])


def clear_google_chat_approval_card_bindings_for_test() -> None:
    approval_card_bindings.clear()
    approval_card_resolving_tokens.clear()
    manual_approval_followup_suppressions.clear()


__all__ = [
    "GOOGLECHAT_APPROVAL_ACTION",
    "create_google_chat_approval_token",
    "build_google_chat_approval_action_parameters",
    "read_google_chat_approval_action_token",
    "register_google_chat_approval_card_binding",
    "get_google_chat_approval_card_binding",
    "claim_google_chat_approval_card_binding",
    "complete_google_chat_approval_card_binding",
    "release_google_chat_approval_card_binding",
    "unregister_google_chat_approval_card_bindings",
    "should_suppress_google_chat_manual_exec_approval_followup_text",
    "should_suppress_google_chat_manual_exec_approval_followup_payload",
    "clear_google_chat_approval_card_bindings_for_test",
]