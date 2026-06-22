"""Cap consecutive idle timeouts before the outer run loop stops."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypedDict

MAX_CONSECUTIVE_IDLE_TIMEOUTS_BEFORE_OUTPUT = 5


@dataclass
class IdleTimeoutBreakerState:
    consecutive_idle_timeouts_before_output: int = 0


def create_idle_timeout_breaker_state() -> IdleTimeoutBreakerState:
    return IdleTimeoutBreakerState()


class IdleTimeoutBreakerInput(TypedDict, total=False):
    idleTimedOut: bool
    completedModelProgress: bool
    outputTokens: int


class IdleTimeoutBreakerStep(TypedDict):
    consecutive: int
    tripped: bool


def step_idle_timeout_breaker(
    state: IdleTimeoutBreakerState,
    input: IdleTimeoutBreakerInput,
    *,
    cap: int | None = None,
) -> IdleTimeoutBreakerStep:
    limit = cap if cap is not None else MAX_CONSECUTIVE_IDLE_TIMEOUTS_BEFORE_OUTPUT
    idle = bool(input.get("idleTimedOut"))
    progress = bool(input.get("completedModelProgress"))

    if idle and not progress:
        state.consecutive_idle_timeouts_before_output += 1
    elif progress:
        state.consecutive_idle_timeouts_before_output = 0

    consecutive = state.consecutive_idle_timeouts_before_output
    return {
        "consecutive": consecutive,
        "tripped": limit > 0 and consecutive >= limit,
    }