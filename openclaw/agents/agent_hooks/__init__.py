"""Agent hooks package — context pruning, session manager registry, compaction.

Mirrors src/agents/agent-hooks/.
"""

from __future__ import annotations

from typing import Any, Generic, TypeVar

T = TypeVar("T")

# --- Compaction instructions ---

DEFAULT_COMPACTION_INSTRUCTIONS = (
    "Write the summary body in the primary language used in the conversation.\n"
    "Focus on factual content: what was discussed, decisions made, and current state.\n"
    "Keep the required summary structure and section headers unchanged.\n"
    "Do not translate or alter code, file paths, identifiers, or error messages."
)

MAX_INSTRUCTION_LENGTH = 800


def _truncate_unicode_safe(s: str, max_code_points: int) -> str:
    if len(s) <= max_code_points:
        return s
    return s[:max_code_points]


def _normalize(s: str | None) -> str | None:
    if s is None:
        return None
    trimmed = s.strip()
    return trimmed or None


def resolve_compaction_instructions(
    event_instructions: str | None,
    runtime_instructions: str | None,
) -> str:
    """Resolve compaction instructions with precedence: event → runtime → default."""
    resolved = (
        _normalize(event_instructions)
        or _normalize(runtime_instructions)
        or DEFAULT_COMPACTION_INSTRUCTIONS
    )
    return _truncate_unicode_safe(resolved, MAX_INSTRUCTION_LENGTH)


def compose_split_turn_instructions(
    turn_prefix_instructions: str,
    resolved_instructions: str,
) -> str:
    """Compose split-turn instructions from SDK prefix and resolved instructions."""
    return f"{turn_prefix_instructions}\n\nAdditional requirements:\n{resolved_instructions}"


# --- Context pruning (re-export from subpackage) ---

from .context_pruning.settings import (  # noqa: E402
    DEFAULT_CONTEXT_PRUNING_SETTINGS,
    compute_effective_settings,
)
from .context_pruning.pruner import prune_context_messages  # noqa: E402

__all__ = [
    "DEFAULT_COMPACTION_INSTRUCTIONS",
    "MAX_INSTRUCTION_LENGTH",
    "resolve_compaction_instructions",
    "compose_split_turn_instructions",
    "DEFAULT_CONTEXT_PRUNING_SETTINGS",
    "compute_effective_settings",
    "prune_context_messages",
    "SessionManagerRuntimeRegistry",
    "create_session_manager_runtime_registry",
]


# --- Session manager runtime registry ---

class SessionManagerRuntimeRegistry(Generic[T]):
    """WeakMap-backed runtime registry keyed by SessionManager object identity."""

    def __init__(self) -> None:
        self._registry: dict[int, T] = {}

    def set(self, session_manager: Any, value: T | None) -> None:
        if session_manager is None:
            return
        key = id(session_manager)
        if value is None:
            self._registry.pop(key, None)
            return
        self._registry[key] = value

    def get(self, session_manager: Any) -> T | None:
        if session_manager is None:
            return None
        return self._registry.get(id(session_manager))


def create_session_manager_runtime_registry() -> SessionManagerRuntimeRegistry:
    """Create a new session manager runtime registry."""
    return SessionManagerRuntimeRegistry()
