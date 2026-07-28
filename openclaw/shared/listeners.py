"""Listener helpers for notifying and registering event listeners."""

from __future__ import annotations

from typing import Any, Callable, Iterable


def notify_listeners(
    listeners: Iterable[Callable[[Any], None]],
    event: Any,
    on_error: Callable[[Any], None] | None = None,
) -> None:
    for listener in listeners:
        try:
            listener(event)
        except Exception as e:
            if on_error:
                on_error(e)


def register_listener(
    listeners: set[Callable[[Any], None]],
    listener: Callable[[Any], None],
) -> Callable[[], None]:
    listeners.add(listener)

    def _unregister() -> None:
        listeners.discard(listener)

    return _unregister
