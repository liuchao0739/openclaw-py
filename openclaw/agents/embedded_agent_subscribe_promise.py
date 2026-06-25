"""Narrow unknown values to awaitable without requiring a concrete coroutine."""

from __future__ import annotations

from typing import Any


def is_awaitable(value: Any) -> bool:
    """Check if a value is awaitable (has a ``__await__`` method or is a coroutine)."""
    import asyncio

    return asyncio.iscoroutine(value) or asyncio.isfuture(value) or (
        hasattr(value, "__await__") and callable(getattr(value, "__await__"))
    )


def is_promise_like(value: Any) -> bool:
    """Check if a value is Promise-like (has a callable ``then`` property)."""
    return bool(
        value
        and (isinstance(value, object) or callable(value))
        and hasattr(value, "then")
        and callable(getattr(value, "then"))
    )
