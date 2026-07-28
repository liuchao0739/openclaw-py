from __future__ import annotations

import random
import time
from typing import Any


def clamp_positive_timer_timeout_ms(ms: int | float) -> int | None:
    if not isinstance(ms, (int, float)):
        return None
    if ms <= 0:
        return None
    return int(min(ms, 2**31 - 1))


def compute_backoff(policy: dict[str, Any], attempt: int) -> int:
    initial_ms = policy.get("initialMs", 100)
    max_ms = policy.get("maxMs", 30000)
    factor = policy.get("factor", 2.0)
    jitter = policy.get("jitter", 0.1)
    base = initial_ms * (factor ** max(attempt - 1, 0))
    jitter_amount = base * jitter * random.random()
    return min(max_ms, round(base + jitter_amount))


def sleep_with_abort(ms: int, abort_signal: Any = None) -> None:
    delay_ms = clamp_positive_timer_timeout_ms(ms)
    if delay_ms is None:
        return
    if abort_signal is not None and getattr(abort_signal, "aborted", False):
        raise Exception("aborted")
    time.sleep(delay_ms / 1000.0)
    if abort_signal is not None and getattr(abort_signal, "aborted", False):
        raise Exception("aborted")
