"""Agent hooks package — context pruning, session manager registry, compaction.

Mirrors src/agents/agent-hooks/.
"""

from __future__ import annotations

import weakref
from typing import Any, Callable, Generic, TypeVar

T = TypeVar("T")

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


# --- Context pruning settings ---

DEFAULT_CONTEXT_PRUNING_SETTINGS = {
    "enabled": False,
    "maxMessages": 0,
    "preserveSystemMessages": True,
    "preserveToolCalls": True,
}


def compute_effective_settings(
    config_settings: dict[str, Any] | None = None,
    session_override: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Compute effective context pruning settings."""
    result = dict(DEFAULT_CONTEXT_PRUNING_SETTINGS)
    if config_settings:
        result.update(config_settings)
    if session_override:
        result.update(session_override)
    return result


def prune_context_messages(
    messages: list[dict[str, Any]],
    settings: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Prune context messages (microcompact-style) — in-memory only."""
    settings = settings or DEFAULT_CONTEXT_PRUNING_SETTINGS
    if not settings.get("enabled"):
        return list(messages)
    max_messages = settings.get("maxMessages", 0)
    if max_messages <= 0:
        return list(messages)
    preserve_system = settings.get("preserveSystemMessages", True)
    preserve_tools = settings.get("preserveToolCalls", True)

    result: list[dict[str, Any]] = []
    preserved: list[dict[str, Any]] = []

    for msg in messages:
        role = msg.get("role", "")
        if preserve_system and role == "system":
            preserved.append(msg)
            continue
        if preserve_tools and role == "tool":
            preserved.append(msg)
            continue
        result.append(msg)

    if len(result) > max_messages:
        result = result[-max_messages:]

    return [*preserved, *result]


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
