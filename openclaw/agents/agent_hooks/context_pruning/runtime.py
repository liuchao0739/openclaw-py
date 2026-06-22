"""Session-manager scoped runtime state for context-pruning extension settings."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from openclaw.agents.agent_hooks.context_pruning.settings import EffectiveContextPruningSettings
from openclaw.agents.agent_hooks.session_manager_runtime_registry import (
    create_session_manager_runtime_registry,
)


@dataclass
class ContextPruningRuntimeValue:
    settings: EffectiveContextPruningSettings
    is_tool_prunable: Callable[[str], bool]
    drop_thinking_blocks: bool
    context_window_tokens: int | None = None
    last_cache_touch_at: int | None = None


_set, _get = create_session_manager_runtime_registry(ContextPruningRuntimeValue)


def set_context_pruning_runtime(
    session_manager: object | None,
    value: ContextPruningRuntimeValue | None,
) -> None:
    _set(session_manager, value)


def get_context_pruning_runtime(session_manager: object | None) -> ContextPruningRuntimeValue | None:
    return _get(session_manager)