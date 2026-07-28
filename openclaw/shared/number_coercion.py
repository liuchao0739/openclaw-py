"""Shared numeric coercion facade."""

from __future__ import annotations

import math
from typing import Any


def resolve_non_negative_number(value: int | float | None) -> int | float | None:
    if not isinstance(value, (int, float)):
        return None
    if not math.isfinite(value) or value < 0:
        return None
    return value
