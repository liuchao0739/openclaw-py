"""Model parameter B helpers infer parameter size from model id or name."""

from __future__ import annotations

import re


def _normalize_lowercase_or_empty(value: str | None) -> str:
    if value is None:
        return ""
    return value.strip().lower()


def infer_param_b_from_id_or_name(text: str) -> int | None:
    raw = _normalize_lowercase_or_empty(text)
    matches = list(re.finditer(r"(?:^|[^a-z0-9])[a-z]?(\d+(?:\.\d+)?)b(?=[^a-z0-9]|$)", raw))
    best: int | None = None
    for match in matches:
        num_raw = match.group(1)
        if not num_raw:
            continue
        try:
            value = float(num_raw)
        except ValueError:
            continue
        if not (value > 0):
            continue
        if best is None or value > best:
            best = int(value) if value == int(value) else value
    return int(best) if best is not None else None
