from __future__ import annotations

from typing import Any

from ._normalization import resolve_integer_option as resolve_shared_integer_option


def resolve_acp_integer_option(value: Any, fallback: int, *, min_value: int) -> int:
    return resolve_shared_integer_option(value, fallback, min_value=min_value)


def resolve_integer_option(value: Any, fallback: int, *, min: int) -> int:
    return resolve_shared_integer_option(value, fallback, min_value=min)