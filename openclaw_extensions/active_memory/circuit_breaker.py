from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class CircuitBreakerEntry:
    consecutive_timeouts: int = 0
    last_timeout_at: float = 0.0


_timeout_circuit_breaker: dict[str, CircuitBreakerEntry] = {}


def build_circuit_breaker_key(agent_id: str, provider: str | None = None, model: str | None = None) -> str:
    return f"{agent_id}:{provider or 'unknown'}/{model or 'unknown'}"


def is_circuit_breaker_open(key: str, max_timeouts: int, cooldown_ms: int) -> bool:
    entry = _timeout_circuit_breaker.get(key)
    if entry is None or entry.consecutive_timeouts < max_timeouts:
        return False
    now_ms = time.time() * 1000
    if now_ms - entry.last_timeout_at >= cooldown_ms:
        _timeout_circuit_breaker.pop(key, None)
        return False
    return True


def record_circuit_breaker_timeout(key: str) -> None:
    entry = _timeout_circuit_breaker.get(key)
    now_ms = time.time() * 1000
    if entry is not None:
        entry.consecutive_timeouts += 1
        entry.last_timeout_at = now_ms
    else:
        _timeout_circuit_breaker[key] = CircuitBreakerEntry(
            consecutive_timeouts=1,
            last_timeout_at=now_ms,
        )


def reset_circuit_breaker(key: str) -> None:
    _timeout_circuit_breaker.pop(key, None)


def get_circuit_breaker_entry(key: str) -> CircuitBreakerEntry | None:
    return _timeout_circuit_breaker.get(key)


def reset_all_circuit_breakers() -> None:
    _timeout_circuit_breaker.clear()