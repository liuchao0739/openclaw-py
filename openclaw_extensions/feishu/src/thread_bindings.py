"""Feishu plugin module implements thread bindings behavior."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Literal

from openclaw.agents.tools.sessions_helpers import parse_session_key
from openclaw.packages.normalization_core import normalize_optional_string
from openclaw.routing.account_id import normalize_account_id

FeishuBindingTargetKind = Literal["subagent", "acp"]
BindingTargetKind = Literal["subagent", "session"]


@dataclass
class FeishuThreadBindingRecord:
    account_id: str
    conversation_id: str
    target_kind: FeishuBindingTargetKind
    target_session_key: str
    bound_at: int
    last_activity_at: int
    parent_conversation_id: str | None = None
    delivery_to: str | None = None
    delivery_thread_id: str | None = None
    agent_id: str | None = None
    label: str | None = None
    bound_by: str | None = None


@dataclass
class FeishuThreadBindingManager:
    account_id: str
    get_by_conversation_id: Any
    list_by_session_key: Any
    bind_conversation: Any
    touch_conversation: Any
    unbind_conversation: Any
    unbind_by_session_key: Any
    stop: Any


@dataclass
class _FeishuThreadBindingsState:
    managers_by_account_id: dict[str, FeishuThreadBindingManager] = field(default_factory=dict)
    bindings_by_account_conversation: dict[str, FeishuThreadBindingRecord] = field(
        default_factory=dict
    )


_STATE_KEY = "openclaw.feishu_thread_bindings_state"


def _get_state() -> _FeishuThreadBindingsState:
    import sys

    module = sys.modules[__name__]
    state = getattr(module, "_feishu_thread_bindings_state", None)
    if state is None:
        state = _FeishuThreadBindingsState()
        module._feishu_thread_bindings_state = state
    return state


def _resolve_binding_key(*, account_id: str, conversation_id: str) -> str:
    return f"{account_id}:{conversation_id}"


def _to_feishu_target_kind(raw: BindingTargetKind) -> FeishuBindingTargetKind:
    return "subagent" if raw == "subagent" else "acp"


def _resolve_agent_id_from_session_key(session_key: str | None) -> str:
    parsed = parse_session_key(session_key or "")
    return parsed.get("agentId") or "main"


def _read_metadata_string(metadata: dict[str, Any] | None, key: str) -> str | None:
    if not metadata:
        return None
    value = metadata.get(key)
    if not isinstance(value, str):
        return None
    trimmed = value.strip()
    return trimmed or None


def create_feishu_thread_binding_manager(
    *,
    cfg: dict[str, Any],
    account_id: str | None = None,
) -> FeishuThreadBindingManager:
    del cfg
    resolved_account_id = normalize_account_id(account_id)
    state = _get_state()
    existing = state.managers_by_account_id.get(resolved_account_id)
    if existing is not None:
        return existing

    def get_by_conversation_id(conversation_id: str) -> FeishuThreadBindingRecord | None:
        return state.bindings_by_account_conversation.get(
            _resolve_binding_key(
                account_id=resolved_account_id,
                conversation_id=conversation_id,
            )
        )

    def list_by_session_key(target_session_key: str) -> list[FeishuThreadBindingRecord]:
        return [
            record
            for record in state.bindings_by_account_conversation.values()
            if record.account_id == resolved_account_id
            and record.target_session_key == target_session_key
        ]

    def bind_conversation(
        *,
        conversation_id: str,
        parent_conversation_id: str | None = None,
        target_kind: BindingTargetKind,
        target_session_key: str,
        metadata: dict[str, Any] | None = None,
    ) -> FeishuThreadBindingRecord | None:
        normalized_conversation_id = conversation_id.strip()
        normalized_target_session_key = target_session_key.strip()
        if not normalized_conversation_id or not normalized_target_session_key:
            return None

        binding_key = _resolve_binding_key(
            account_id=resolved_account_id,
            conversation_id=normalized_conversation_id,
        )
        existing_local = state.bindings_by_account_conversation.get(binding_key)
        now = int(time.time() * 1000)
        record = FeishuThreadBindingRecord(
            account_id=resolved_account_id,
            conversation_id=normalized_conversation_id,
            parent_conversation_id=(
                normalize_optional_string(parent_conversation_id)
                or (existing_local.parent_conversation_id if existing_local else None)
            ),
            delivery_to=(
                _read_metadata_string(metadata, "deliveryTo")
                or (existing_local.delivery_to if existing_local else None)
            ),
            delivery_thread_id=(
                _read_metadata_string(metadata, "deliveryThreadId")
                or (existing_local.delivery_thread_id if existing_local else None)
            ),
            target_kind=_to_feishu_target_kind(target_kind),
            target_session_key=normalized_target_session_key,
            agent_id=(
                _read_metadata_string(metadata, "agentId")
                or (existing_local.agent_id if existing_local else None)
                or _resolve_agent_id_from_session_key(normalized_target_session_key)
            ),
            label=(
                _read_metadata_string(metadata, "label")
                or (existing_local.label if existing_local else None)
            ),
            bound_by=(
                _read_metadata_string(metadata, "boundBy")
                or (existing_local.bound_by if existing_local else None)
            ),
            bound_at=now,
            last_activity_at=now,
        )
        state.bindings_by_account_conversation[binding_key] = record
        return record

    def touch_conversation(
        conversation_id: str,
        at: int | None = None,
    ) -> FeishuThreadBindingRecord | None:
        binding_key = _resolve_binding_key(
            account_id=resolved_account_id,
            conversation_id=conversation_id,
        )
        existing_record = state.bindings_by_account_conversation.get(binding_key)
        if existing_record is None:
            return None
        updated = FeishuThreadBindingRecord(
            **{
                **existing_record.__dict__,
                "last_activity_at": at if at is not None else int(time.time() * 1000),
            }
        )
        state.bindings_by_account_conversation[binding_key] = updated
        return updated

    def unbind_conversation(conversation_id: str) -> FeishuThreadBindingRecord | None:
        binding_key = _resolve_binding_key(
            account_id=resolved_account_id,
            conversation_id=conversation_id,
        )
        existing_record = state.bindings_by_account_conversation.pop(binding_key, None)
        return existing_record

    def unbind_by_session_key(target_session_key: str) -> list[FeishuThreadBindingRecord]:
        removed: list[FeishuThreadBindingRecord] = []
        for key, record in list(state.bindings_by_account_conversation.items()):
            if (
                record.account_id != resolved_account_id
                or record.target_session_key != target_session_key
            ):
                continue
            state.bindings_by_account_conversation.pop(key, None)
            removed.append(record)
        return removed

    def stop() -> None:
        for key in list(state.bindings_by_account_conversation.keys()):
            if key.startswith(f"{resolved_account_id}:"):
                state.bindings_by_account_conversation.pop(key, None)
        state.managers_by_account_id.pop(resolved_account_id, None)

    manager = FeishuThreadBindingManager(
        account_id=resolved_account_id,
        get_by_conversation_id=get_by_conversation_id,
        list_by_session_key=list_by_session_key,
        bind_conversation=bind_conversation,
        touch_conversation=touch_conversation,
        unbind_conversation=unbind_conversation,
        unbind_by_session_key=unbind_by_session_key,
        stop=stop,
    )
    state.managers_by_account_id[resolved_account_id] = manager
    return manager


def get_feishu_thread_binding_manager(
    account_id: str | None = None,
) -> FeishuThreadBindingManager | None:
    return _get_state().managers_by_account_id.get(normalize_account_id(account_id))


class _FeishuThreadBindingTesting:
    @staticmethod
    def reset_feishu_thread_bindings_for_tests() -> None:
        state = _get_state()
        for manager in list(state.managers_by_account_id.values()):
            manager.stop()
        state.managers_by_account_id.clear()
        state.bindings_by_account_conversation.clear()


testing = _FeishuThreadBindingTesting()
__testing = testing

__all__ = [
    "FeishuThreadBindingManager",
    "FeishuThreadBindingRecord",
    "__testing",
    "create_feishu_thread_binding_manager",
    "get_feishu_thread_binding_manager",
    "testing",
]
