"""Shared string sampling for operator logs and SDK helpers."""

from __future__ import annotations

import math
from typing import Any


def summarize_string_entries(
    entries: list[str] | None = None,
    limit: int | None = None,
    empty_text: str = "",
) -> str:
    if entries is None:
        entries = []
    if len(entries) == 0:
        return empty_text
    raw_limit = limit if limit is not None else 6
    if not math.isfinite(raw_limit):
        raw_limit = 6
    limit = max(1, int(raw_limit))
    sample = entries[:limit]
    suffix = f" (+{len(entries) - len(sample)})" if len(entries) > len(sample) else ""
    return f"{', '.join(sample)}{suffix}"
