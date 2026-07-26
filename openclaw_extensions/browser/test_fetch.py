"""Test fetch helper that adds no-op preconnect support expected by Browser tests."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

FetchPreconnectOptions = Mapping[str, bool]

T = TypeVar("T")


def with_browser_fetch_preconnect(fn: T) -> T:
    """Add Browser test preconnect metadata to a fetch-like function."""

    def preconnect(_url: str | Any, _options: FetchPreconnectOptions | None = None) -> None:
        return None

    if isinstance(fn, dict):
        fn["preconnect"] = preconnect
        fn["__openclawAcceptsDispatcher"] = True
        return fn

    fn.preconnect = preconnect
    fn.__openclawAcceptsDispatcher = True  # type: ignore[attr-defined]
    return fn
