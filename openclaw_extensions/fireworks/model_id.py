"""Fireworks plugin model id helpers."""

from __future__ import annotations

import re

_KIMI_MODEL_ID_PATTERN = re.compile(r"^kimi-k2(?:p[56]|[.-][56])(?:[-_].+)?$")


def is_fireworks_kimi_model_id(model_id: str) -> bool:
    normalized = model_id.strip().lower()
    last_segment = normalized.rsplit("/", 1)[-1]
    return _KIMI_MODEL_ID_PATTERN.fullmatch(last_segment) is not None
