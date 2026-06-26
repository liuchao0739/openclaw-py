"""Coerces cron schedule number fields with strict finite-number parsing.

Mirrors src/cron/schedule-number.ts.
"""

from __future__ import annotations

import math
from typing import Any


def coerce_finite_schedule_number(value: Any) -> float | None:
    """Coerce schedule numeric fields without accepting partial or non-finite numbers.

    Accepts int and float (excluding bool). Rejects strings, None, NaN, inf.
    """
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return float(value)
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
        return value
    return None
