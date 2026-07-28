"""Deferred event buffer for collecting events and flushing them later."""

from __future__ import annotations

from typing import Any, Callable


def create_deferred_event_buffer(
    sink: Any,
    on_buffered_event: Callable[[], None] | None = None,
) -> dict[str, Any]:
    events: list[Any] = []

    def push(event: Any) -> None:
        events.append(event)
        if on_buffered_event:
            on_buffered_event()

    def flush() -> None:
        for event in events:
            sink.push(event)
        events.clear()

    def discard() -> None:
        events.clear()

    return {"push": push, "flush": flush, "discard": discard}
