"""Session-manager scoped runtime state for compaction safeguard configuration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from openclaw.agents.agent_hooks.session_manager_runtime_registry import (
    create_session_manager_runtime_registry,
)
from openclaw.llm.core import Model


@dataclass
class CompactionSafeguardRuntimeValue:
    max_history_share: float | None = None
    context_window_tokens: int | None = None
    identifier_policy: str | None = None
    identifier_instructions: str | None = None
    custom_instructions: str | None = None
    model: Model | None = None
    recent_turns_preserve: int | None = None
    workspace_dir: str | None = None
    post_compaction_sections: list[str] | None = None
    quality_guard_enabled: bool | None = None
    quality_guard_max_retries: int | None = None
    provider: str | None = None
    cancel_reason: str | None = None


_set, _get = create_session_manager_runtime_registry(CompactionSafeguardRuntimeValue)


def set_compaction_safeguard_runtime(
    session_manager: object | None,
    value: CompactionSafeguardRuntimeValue | None,
) -> None:
    _set(session_manager, value)


def get_compaction_safeguard_runtime(
    session_manager: object | None,
) -> CompactionSafeguardRuntimeValue | None:
    return _get(session_manager)


def set_compaction_safeguard_cancel_reason(
    session_manager: object | None,
    reason: str | None,
) -> None:
    current = get_compaction_safeguard_runtime(session_manager)
    trimmed = reason.strip() if isinstance(reason, str) else None
    trimmed = trimmed if trimmed else None

    if not current:
        if not trimmed:
            return
        set_compaction_safeguard_runtime(
            session_manager,
            CompactionSafeguardRuntimeValue(cancel_reason=trimmed),
        )
        return

    next_val = CompactionSafeguardRuntimeValue(**{**current.__dict__})
    if trimmed:
        next_val.cancel_reason = trimmed
    else:
        next_val.cancel_reason = None
    set_compaction_safeguard_runtime(session_manager, next_val)


def consume_compaction_safeguard_cancel_reason(session_manager: object | None) -> str | None:
    current = get_compaction_safeguard_runtime(session_manager)
    if not current or not current.cancel_reason:
        return None
    reason = current.cancel_reason.strip()
    if not reason:
        return None
    rest = {k: v for k, v in current.__dict__.items() if k != "cancel_reason" and v is not None}
    if rest:
        set_compaction_safeguard_runtime(session_manager, CompactionSafeguardRuntimeValue(**rest))
    else:
        set_compaction_safeguard_runtime(session_manager, None)
    return reason