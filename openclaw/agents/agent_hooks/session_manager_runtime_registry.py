"""WeakMap-backed runtime registry keyed by SessionManager object identity."""

from __future__ import annotations

from typing import Callable, TypeVar

TValue = TypeVar("TValue")


def create_session_manager_runtime_registry(
    _value_type: type[TValue],  # noqa: ARG001 — mirrors TS generic
) -> tuple[
    Callable[[object | None, TValue | None], None],
    Callable[[object | None], TValue | None],
]:
    registry: dict[int, TValue] = {}

    def set_value(session_manager: object | None, value: TValue | None) -> None:
        if session_manager is None or not isinstance(session_manager, object):
            return
        key = id(session_manager)
        if value is None:
            registry.pop(key, None)
            return
        registry[key] = value

    def get_value(session_manager: object | None) -> TValue | None:
        if session_manager is None or not isinstance(session_manager, object):
            return None
        return registry.get(id(session_manager))

    return set_value, get_value