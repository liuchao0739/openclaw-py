from __future__ import annotations

import math
from typing import Any, Callable, Mapping

from ._normalization import normalize_optional_string


def read_meta_value(
    meta: Mapping[str, Any] | None,
    keys: list[str],
    normalize: Callable[[Any], Any | None],
) -> Any | None:
    if not meta:
        return None
    for key in keys:
        normalized = normalize(meta.get(key))
        if normalized is not None:
            return normalized
    return None


def read_string(meta: Mapping[str, Any] | None, keys: list[str]) -> str | None:
    return read_meta_value(meta, keys, normalize_optional_string)


def read_bool(meta: Mapping[str, Any] | None, keys: list[str]) -> bool | None:
    return read_meta_value(meta, keys, lambda v: v if isinstance(v, bool) else None)


def read_number(meta: Mapping[str, Any] | None, keys: list[str]) -> float | None:
    def _normalize(v: Any) -> float | None:
        if isinstance(v, bool):
            return None
        if isinstance(v, (int, float)) and math.isfinite(v):
            return float(v)
        return None

    return read_meta_value(meta, keys, _normalize)


def read_non_negative_integer(meta: Mapping[str, Any] | None, keys: list[str]) -> int | None:
    def _normalize(v: Any) -> int | None:
        if isinstance(v, bool):
            return None
        if isinstance(v, int) and v >= 0:
            return v
        if isinstance(v, float) and math.isfinite(v) and v == int(v) and v >= 0:
            return int(v)
        return None

    return read_meta_value(meta, keys, _normalize)