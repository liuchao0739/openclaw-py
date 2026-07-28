from __future__ import annotations

import asyncio
import time
from typing import Any, Callable, Optional


def _sleep(ms: int) -> None:
    time.sleep(ms / 1000.0)


def _as_finite_number(value: object) -> Optional[float]:
    if not isinstance(value, (int, float)):
        return None
    fv = float(value)
    if fv != fv:
        return None
    return fv


def _clamp_number(value: object, fallback: float, min_val: Optional[float] = None, max_val: Optional[float] = None) -> float:
    result = _as_finite_number(value)
    if result is None:
        return fallback
    floor = min_val if min_val is not None else float("-inf")
    ceiling = max_val if max_val is not None else float("inf")
    return min(max(result, floor), ceiling)


def _resolve_attempts(value: object, fallback: int) -> int:
    if not isinstance(value, int) or value != int(value) or value < 1:
        return fallback
    return max(1, value)


def _resolve_safe_timeout_delay_ms(value: float, opts: Optional[dict] = None) -> float:
    min_ms = (opts or {}).get("minMs", 0)
    return max(value, min_ms)


DEFAULT_RETRY_CONFIG = {
    "attempts": 3,
    "minDelayMs": 300,
    "maxDelayMs": 30_000,
    "jitter": 0,
}


def resolve_retry_config(defaults: Optional[dict] = None, overrides: Optional[dict] = None) -> dict:
    base = defaults or DEFAULT_RETRY_CONFIG
    attempts = _resolve_attempts(overrides.get("attempts") if overrides else None, base["attempts"])
    min_delay_ms = _resolve_safe_timeout_delay_ms(
        round(_clamp_number(overrides.get("minDelayMs") if overrides else None, base["minDelayMs"], 0)),
        {"minMs": 0},
    )
    max_delay_ms = max(
        min_delay_ms,
        _resolve_safe_timeout_delay_ms(
            round(_clamp_number(overrides.get("maxDelayMs") if overrides else None, base["maxDelayMs"], 0)),
            {"minMs": 0},
        ),
    )
    jitter = _clamp_number(overrides.get("jitter") if overrides else None, base["jitter"], 0, 1)
    return {"attempts": attempts, "minDelayMs": min_delay_ms, "maxDelayMs": max_delay_ms, "jitter": jitter}


def _apply_jitter(delay_ms: float, jitter: float) -> float:
    if jitter <= 0:
        return delay_ms
    import random
    offset = (random.random() * 2 - 1) * jitter
    return max(0, round(delay_ms * (1 + offset)))


def _to_lint_error_object(value: object, fallback_message: str) -> Exception:
    if isinstance(value, Exception):
        return value
    if isinstance(value, str):
        return Exception(value)
    error = Exception(fallback_message)
    if isinstance(value, (dict, list)):
        error.__dict__.update(value if isinstance(value, dict) else {})
    return error


def retry_async(fn: Callable, attempts_or_options: Any = 3, initial_delay_ms: float = 300) -> Any:
    if isinstance(attempts_or_options, (int, float)):
        attempts = _resolve_attempts(attempts_or_options, DEFAULT_RETRY_CONFIG["attempts"])
        last_err = None
        for i in range(attempts):
            try:
                return fn()
            except Exception as e:
                last_err = e
                if i >= attempts - 1:
                    break
                _sleep(_resolve_safe_timeout_delay_ms(initial_delay_ms * (2**i), {"minMs": 0}))
        raise _to_lint_error_object(last_err or Exception("Retry failed"), "Non-Error thrown")

    options = attempts_or_options
    resolved = resolve_retry_config(DEFAULT_RETRY_CONFIG, options)
    max_attempts = resolved["attempts"]
    min_delay_ms = resolved["minDelayMs"]
    max_delay_ms = float("inf") if resolved["maxDelayMs"] == float("inf") else resolved["maxDelayMs"]
    should_retry = options.get("shouldRetry") if options else None
    last_err = None

    for attempt in range(1, max_attempts + 1):
        try:
            return fn()
        except Exception as e:
            last_err = e
            if attempt >= max_attempts or (should_retry and not should_retry(e, attempt)):
                break

            retry_after_ms = options.get("retryAfterMs")(e) if options and options.get("retryAfterMs") else None
            if isinstance(retry_after_ms, (int, float)) and retry_after_ms == retry_after_ms:
                base_delay = max(
                    _resolve_safe_timeout_delay_ms(retry_after_ms, {"minMs": 0}),
                    min_delay_ms,
                )
            else:
                base_delay = _resolve_safe_timeout_delay_ms(
                    min_delay_ms * (2 ** (attempt - 1)),
                    {"minMs": 0},
                )
            delay = min(base_delay, max_delay_ms)
            delay = _apply_jitter(delay, resolved["jitter"])
            delay = min(max(delay, min_delay_ms), max_delay_ms)

            if options and options.get("onRetry"):
                options["onRetry"]({
                    "attempt": attempt,
                    "maxAttempts": max_attempts,
                    "delayMs": delay,
                    "err": e,
                    "label": options.get("label"),
                })
            if delay > 0:
                _sleep(delay)

    raise _to_lint_error_object(last_err or Exception("Retry failed"), "Non-Error thrown")
