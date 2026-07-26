"""Public SDK helper for caching a lazily computed value behind a getter."""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")


def create_cached_lazy_value_getter(
    value: T | Callable[[], T | None] | None,
    fallback: T | None = None,
) -> Callable[[], T | None]:
    """Return a getter that resolves the supplied value at most once."""
    resolved = False
    cached: T | None = None

    def getter() -> T | None:
        nonlocal resolved, cached
        if not resolved:
            next_value = value() if callable(value) else value
            cached = fallback if next_value is None else next_value
            resolved = True
        return cached

    return getter
