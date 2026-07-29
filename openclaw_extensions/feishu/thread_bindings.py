import time
from typing import Any, Optional, Callable

from .accounts import _normalize_account_id

FEISHU_THREAD_BINDINGS_STATE_KEY = "openclaw.feishuThreadBindingsState"

_state: Optional[dict] = None


def _get_state() -> dict:
    global _state
    if _state is None:
        store = globals()
        existing = store.get("__feishu_thread_bindings_state__")
        if existing is None:
            existing = {
                "managersByAccountId": {},
                "bindingsByAccountConversation": {},
            }
        _state = existing
        store["__feishu_thread_bindings_state__"] = _state
    return _state


def _resolve_binding_key(params: dict) -> str:
    return f'{params["accountId"]}:{params["conversationId"]}'


def _to_session_binding_target_kind(raw: str) -> str:
    return "subagent" if raw == "subagent" else "session"


def _to_feishu_target_kind(raw: str) -> str:
    return "subagent" if raw == "subagent" else "acp"


def _now_ms() -> int:
    return int(time.time() * 1000)


def _normalize_optional_string(value: Any) -> Optional[str]:
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    return cleaned or None


def _resolve_agent_id_from_session_key(session_key: str) -> Optional[str]:
    if not session_key:
        return None
    parts = session_key.split(":", 1)
    return parts[0] if parts else None


def _to_session_binding_record(record: dict, defaults: dict) -> dict:
    idle_expires_at = record["lastActivityAt"] + defaults["idleTimeoutMs"] if defaults["idleTimeoutMs"] > 0 else None
    max_age_expires_at = record["boundAt"] + defaults["maxAgeMs"] if defaults["maxAgeMs"] > 0 else None
    if idle_expires_at is not None and max_age_expires_at is not None:
        expires_at = min(idle_expires_at, max_age_expires_at)
    else:
        expires_at = idle_expires_at if idle_expires_at is not None else max_age_expires_at
    return {
        "bindingId": _resolve_binding_key({"accountId": record["accountId"], "conversationId": record["conversationId"]}),
        "targetSessionKey": record["targetSessionKey"],
        "targetKind": _to_session_binding_target_kind(record["targetKind"]),
        "conversation": {
            "channel": "feishu",
            "accountId": record["accountId"],
            "conversationId": record["conversationId"],
            "parentConversationId": record.get("parentConversationId"),
        },
        "status": "active",
        "boundAt": record["boundAt"],
        "expiresAt": expires_at,
        "metadata": {
            "agentId": record.get("agentId"),
            "label": record.get("label"),
            "boundBy": record.get("boundBy"),
            "deliveryTo": record.get("deliveryTo"),
            "deliveryThreadId": record.get("deliveryThreadId"),
            "lastActivityAt": record["lastActivityAt"],
            "idleTimeoutMs": defaults["idleTimeoutMs"],
            "maxAgeMs": defaults["maxAgeMs"],
        },
    }


def create_feishu_thread_binding_manager(params: dict) -> dict:
    account_id = _normalize_account_id(params.get("accountId"))
    state = _get_state()
    existing = state["managersByAccountId"].get(account_id)
    if existing:
        return existing

    idle_timeout_ms = 0
    max_age_ms = 0

    def get_by_conversation_id(conversation_id: str) -> Optional[dict]:
        return state["bindingsByAccountConversation"].get(_resolve_binding_key({"accountId": account_id, "conversationId": conversation_id}))

    def list_by_session_key(target_session_key: str) -> list:
        return [
            record for record in state["bindingsByAccountConversation"].values()
            if record["accountId"] == account_id and record["targetSessionKey"] == target_session_key
        ]

    def bind_conversation(bind_params: dict) -> Optional[dict]:
        normalized_conversation_id = bind_params.get("conversationId", "").strip()
        normalized_target_session_key = bind_params.get("targetSessionKey", "").strip()
        if not normalized_conversation_id or not normalized_target_session_key:
            return None
        existing_local = state["bindingsByAccountConversation"].get(_resolve_binding_key({"accountId": account_id, "conversationId": normalized_conversation_id}))
        now = _now_ms()
        metadata = bind_params.get("metadata") or {}
        record = {
            "accountId": account_id,
            "conversationId": normalized_conversation_id,
            "parentConversationId": _normalize_optional_string(bind_params.get("parentConversationId")) or (existing_local or {}).get("parentConversationId"),
            "deliveryTo": _normalize_optional_string(metadata.get("deliveryTo")) or (existing_local or {}).get("deliveryTo"),
            "deliveryThreadId": _normalize_optional_string(metadata.get("deliveryThreadId")) or (existing_local or {}).get("deliveryThreadId"),
            "targetKind": _to_feishu_target_kind(bind_params.get("targetKind", "session")),
            "targetSessionKey": normalized_target_session_key,
            "agentId": _normalize_optional_string(metadata.get("agentId")) or (existing_local or {}).get("agentId") or _resolve_agent_id_from_session_key(normalized_target_session_key),
            "label": _normalize_optional_string(metadata.get("label")) or (existing_local or {}).get("label"),
            "boundBy": _normalize_optional_string(metadata.get("boundBy")) or (existing_local or {}).get("boundBy"),
            "boundAt": now,
            "lastActivityAt": now,
        }
        state["bindingsByAccountConversation"][_resolve_binding_key({"accountId": account_id, "conversationId": normalized_conversation_id})] = record
        return record

    def touch_conversation(conversation_id: str, at: Optional[int] = None) -> Optional[dict]:
        key = _resolve_binding_key({"accountId": account_id, "conversationId": conversation_id})
        existing_record = state["bindingsByAccountConversation"].get(key)
        if not existing_record:
            return None
        updated = dict(existing_record)
        updated["lastActivityAt"] = at if at is not None else _now_ms()
        state["bindingsByAccountConversation"][key] = updated
        return updated

    def unbind_conversation(conversation_id: str) -> Optional[dict]:
        key = _resolve_binding_key({"accountId": account_id, "conversationId": conversation_id})
        existing_record = state["bindingsByAccountConversation"].get(key)
        if not existing_record:
            return None
        state["bindingsByAccountConversation"].pop(key, None)
        return existing_record

    def unbind_by_session_key(target_session_key: str) -> list:
        removed = []
        for record in list(state["bindingsByAccountConversation"].values()):
            if record["accountId"] != account_id or record["targetSessionKey"] != target_session_key:
                continue
            state["bindingsByAccountConversation"].pop(_resolve_binding_key({"accountId": account_id, "conversationId": record["conversationId"]}), None)
            removed.append(record)
        return removed

    def stop() -> None:
        for key in list(state["bindingsByAccountConversation"].keys()):
            if key.startswith(f"{account_id}:"):
                state["bindingsByAccountConversation"].pop(key, None)
        state["managersByAccountId"].pop(account_id, None)

    manager = {
        "accountId": account_id,
        "getByConversationId": get_by_conversation_id,
        "listBySessionKey": list_by_session_key,
        "bindConversation": bind_conversation,
        "touchConversation": touch_conversation,
        "unbindConversation": unbind_conversation,
        "unbindBySessionKey": unbind_by_session_key,
        "stop": stop,
    }

    defaults = {"idleTimeoutMs": idle_timeout_ms, "maxAgeMs": max_age_ms}

    session_binding_adapter = {
        "channel": "feishu",
        "accountId": account_id,
        "capabilities": {"placements": ["current"]},
        "bind": lambda inp: (
            None if (not isinstance(inp, dict) or isinstance(inp, dict) and inp.get("conversation", {}).get("channel") != "feishu" or inp.get("placement") == "child")
            else (
                (lambda bound: _to_session_binding_record(bound, defaults) if bound else None)(
                    manager["bindConversation"]({
                        "conversationId": inp["conversation"]["conversationId"],
                        "parentConversationId": inp["conversation"].get("parentConversationId"),
                        "targetKind": inp.get("targetKind", "session"),
                        "targetSessionKey": inp.get("targetSessionKey", ""),
                        "metadata": inp.get("metadata"),
                    })
                )
            )
        ),
        "listBySession": lambda target_session_key: [_to_session_binding_record(entry, defaults) for entry in manager["listBySessionKey"](target_session_key)],
        "resolveByConversation": lambda ref: (None if not isinstance(ref, dict) or ref.get("channel") != "feishu" else (lambda found: _to_session_binding_record(found, defaults) if found else None)(manager["getByConversationId"](ref.get("conversationId", "")))),
        "touch": lambda binding_id, at=None: None,
        "unbind": lambda inp: [],
    }
    manager["_sessionBindingAdapter"] = session_binding_adapter

    state["managersByAccountId"][account_id] = manager
    return manager


def get_feishu_thread_binding_manager(account_id: Optional[str] = None) -> Optional[dict]:
    return _get_state()["managersByAccountId"].get(_normalize_account_id(account_id))


def reset_feishu_thread_bindings_for_tests() -> None:
    state = _get_state()
    for manager in list(state["managersByAccountId"].values()):
        manager["stop"]()
    state["managersByAccountId"].clear()
    state["bindingsByAccountConversation"].clear()


testing = {"resetFeishuThreadBindingsForTests": reset_feishu_thread_bindings_for_tests}
__testing = testing
