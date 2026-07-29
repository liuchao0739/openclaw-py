from __future__ import annotations

import math


def format_token_count(value: float | None) -> str:
    if value is None or not math.isfinite(value):
        return "0"
    safe = max(0, value)
    if safe >= 1_000_000:
        return f"{safe / 1_000_000:.1f}m"
    if safe >= 1_000:
        precision = 0 if safe >= 10_000 else 1
        formatted_thousands = f"{safe / 1_000:.{precision}f}"
        if float(formatted_thousands) >= 1_000:
            return f"{safe / 1_000_000:.1f}m"
        return f"{formatted_thousands}k"
    return str(round(safe))
