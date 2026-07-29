from __future__ import annotations

import os
import re
import time
from typing import Any

MAX_SAFE_TIMEOUT_DELAY_MS = 2**31 - 1
_SAFE_TIMEOUT_GRACE_MS = 1000


def resolve_safe_timeout_delay_ms(delay_ms: Any, opts: dict | None = None) -> int:
    options = opts or {}
    min_ms = options.get("minMs", 1)
    if isinstance(delay_ms, bool):
        delay_ms = 0
    try:
        delay = int(delay_ms)
    except (ValueError, TypeError):
        delay = 0
    if delay < 0:
        delay = 0
    if delay > MAX_SAFE_TIMEOUT_DELAY_MS:
        delay = MAX_SAFE_TIMEOUT_DELAY_MS
    return max(min_ms, delay)


def resolve_finite_timeout_delay_ms(delay_ms: Any, opts: dict | None = None) -> int | None:
    if isinstance(delay_ms, bool):
        return None
    try:
        delay = int(delay_ms)
    except (ValueError, TypeError):
        return None
    if delay < 0:
        return None
    return resolve_safe_timeout_delay_ms(delay, opts)


def add_safe_timeout_delay_grace_ms(delay_ms: Any, opts: dict | None = None) -> int:
    base = resolve_safe_timeout_delay_ms(delay_ms, opts)
    grace = _SAFE_TIMEOUT_GRACE_MS
    total = base + grace
    if total > MAX_SAFE_TIMEOUT_DELAY_MS:
        return MAX_SAFE_TIMEOUT_DELAY_MS
    return total


def set_safe_timeout(callback: Any, delay_ms: int, opts: dict | None = None) -> Any:
    import threading

    resolved = resolve_safe_timeout_delay_ms(delay_ms, opts)
    timer = threading.Timer(resolved / 1000.0, callback)
    timer.daemon = True
    timer.start()
    return timer
