"""Agent hook history window helpers.

Mirrors src/agents/harness/hook-history.ts.
"""

from __future__ import annotations

from typing import Any

MAX_AGENT_HOOK_HISTORY_MESSAGES = 100


def limit_agent_hook_history_messages(
    messages: list[Any],
    max_messages: int = MAX_AGENT_HOOK_HISTORY_MESSAGES,
) -> list[Any]:
    """Return the tail of hook history capped at the configured maximum."""
    if max_messages <= 0:
        return []
    return messages[-max_messages:]


def build_agent_hook_conversation_messages(
    history_messages: list[Any] | None = None,
    current_turn_messages: list[Any] | None = None,
) -> list[Any]:
    """Build hook-visible conversation messages from bounded history plus current turn."""
    return [
        *limit_agent_hook_history_messages(history_messages or []),
        *(current_turn_messages or []),
    ]
