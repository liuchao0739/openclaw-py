"""LLM request activity listeners for abort signal notifications."""

from __future__ import annotations

import threading
from typing import Any, Callable

_request_activity_listeners: dict[int, set[Callable[[], None]]] = {}
_lock = threading.Lock()


def notify_llm_request_activity(signal: Any) -> None:
    if signal is None:
        return
    sig_id = id(signal)
    with _lock:
        listeners = _request_activity_listeners.get(sig_id, set())
    for listener in listeners:
        try:
            listener()
        except Exception:
            pass


def on_llm_request_activity(
    signal: Any,
    listener: Callable[[], None],
) -> Callable[[], None]:
    sig_id = id(signal)
    with _lock:
        if sig_id not in _request_activity_listeners:
            _request_activity_listeners[sig_id] = set()
        _request_activity_listeners[sig_id].add(listener)

    def _off() -> None:
        with _lock:
            if sig_id in _request_activity_listeners:
                _request_activity_listeners[sig_id].discard(listener)
                if len(_request_activity_listeners[sig_id]) == 0:
                    del _request_activity_listeners[sig_id]

    return _off
