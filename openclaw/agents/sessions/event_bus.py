"""Tiny event bus abstraction for session UI/runtime notifications.

Isolates handler failures so one bad subscriber cannot break later listeners.
"""

from __future__ import annotations

from typing import Any, Callable


class EventBus:
    """Minimal publish/subscribe interface used by session components."""

    def __init__(self) -> None:
        self._listeners: dict[str, list[Callable[[Any], None]]] = {}

    def emit(self, channel: str, data: Any) -> None:
        """Emit data to all listeners on a channel."""
        for handler in list(self._listeners.get(channel, [])):
            try:
                handler(data)
            except Exception as err:
                import sys

                print(f"Event handler error ({channel}): {err}", file=sys.stderr)

    def on(self, channel: str, handler: Callable[[Any], None]) -> Callable[[], None]:
        """Subscribe to a channel. Returns an unsubscribe function."""
        self._listeners.setdefault(channel, []).append(handler)

        def _unsubscribe() -> None:
            handlers = self._listeners.get(channel, [])
            if handler in handlers:
                handlers.remove(handler)

        return _unsubscribe

    def clear(self) -> None:
        """Remove all listeners."""
        self._listeners.clear()


def create_event_bus() -> EventBus:
    """Create an in-process event bus with unsubscribe and clear support."""
    return EventBus()
