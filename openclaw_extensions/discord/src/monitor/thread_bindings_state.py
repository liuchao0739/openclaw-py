"""Discord plugin module implements thread bindings.state behavior."""

from __future__ import annotations

from openclaw.routing.account_id import normalize_account_id
from openclaw_extensions.discord.src.monitor.thread_bindings_types import (
    ThreadBindingRecord,
    ThreadBindingTargetKind,
)

BINDINGS_BY_THREAD_ID: dict[str, ThreadBindingRecord] = {}
MANAGERS_BY_ACCOUNT_ID: dict[str, object] = {}


def normalize_thread_id(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def resolve_binding_record_key(record: ThreadBindingRecord) -> str:
    return f"{record.account_id}:{record.thread_id}"


def resolve_binding_ids_for_session(
    *,
    target_session_key: str,
    account_id: str | None = None,
    target_kind: ThreadBindingTargetKind | None = None,
) -> list[str]:
    ids: list[str] = []
    for key, record in BINDINGS_BY_THREAD_ID.items():
        if record.target_session_key != target_session_key:
            continue
        if account_id and record.account_id != normalize_account_id(account_id):
            continue
        if target_kind and record.target_kind != target_kind:
            continue
        ids.append(key)
    return ids


def set_binding_record(record: ThreadBindingRecord) -> None:
    BINDINGS_BY_THREAD_ID[resolve_binding_record_key(record)] = record


def remove_binding_record(record: ThreadBindingRecord) -> None:
    BINDINGS_BY_THREAD_ID.pop(resolve_binding_record_key(record), None)


def get_thread_binding_manager(account_id: str | None = None):
    return MANAGERS_BY_ACCOUNT_ID.get(normalize_account_id(account_id))


def reset_thread_bindings_for_tests() -> None:
    BINDINGS_BY_THREAD_ID.clear()
    MANAGERS_BY_ACCOUNT_ID.clear()


class _Testing:
    @staticmethod
    def reset_thread_bindings_for_tests() -> None:
        reset_thread_bindings_for_tests()


testing = _Testing()

__all__ = [
    "BINDINGS_BY_THREAD_ID",
    "MANAGERS_BY_ACCOUNT_ID",
    "get_thread_binding_manager",
    "normalize_thread_id",
    "remove_binding_record",
    "reset_thread_bindings_for_tests",
    "resolve_binding_ids_for_session",
    "resolve_binding_record_key",
    "set_binding_record",
    "testing",
]
