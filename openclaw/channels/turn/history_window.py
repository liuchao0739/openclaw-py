"""History window helpers for channel turns.

Bounds conversation history before it is sent to the agent loop.
"""

from __future__ import annotations

from typing import Any

DEFAULT_HISTORY_WINDOW = 50
MAX_HISTORY_WINDOW = 200


def resolve_history_window(
    config: dict[str, Any] | None = None,
    *,
    default: int = DEFAULT_HISTORY_WINDOW,
) -> int:
    """Resolve the history window size from config."""
    if not config:
        return default

    agents = config.get("agents", {})
    if isinstance(agents, dict):
        defaults = agents.get("defaults", {})
        if isinstance(defaults, dict):
            window = defaults.get("historyWindow")
            if isinstance(window, int) and window > 0:
                return min(window, MAX_HISTORY_WINDOW)

    return default


def apply_history_window(
    messages: list[dict[str, Any]],
    window: int = DEFAULT_HISTORY_WINDOW,
) -> list[dict[str, Any]]:
    """Apply a history window to a list of messages, keeping the most recent."""
    if window <= 0 or len(messages) <= window:
        return messages
    return messages[-window:]


def should_compact_history(
    messages: list[dict[str, Any]],
    window: int = DEFAULT_HISTORY_WINDOW,
    *,
    compaction_threshold: float = 0.8,
) -> bool:
    """Check if history should be compacted based on window utilization."""
    if not messages or window <= 0:
        return False
    return len(messages) >= window * compaction_threshold
