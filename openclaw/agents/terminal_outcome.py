"""Agent run terminal outcome normalization."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel


class AgentRunWaitStatus(StrEnum):
    OK = "ok"
    ERROR = "error"
    TIMEOUT = "timeout"


class AgentRunTerminalReason(StrEnum):
    COMPLETED = "completed"
    HARD_TIMEOUT = "hard_timeout"
    TIMED_OUT = "timed_out"
    CANCELLED = "cancelled"
    ABORTED = "aborted"
    BLOCKED = "blocked"
    FAILED = "failed"


HARD_TIMEOUT_PHASES = {"preflight", "provider", "post_turn"}


class AgentRunTerminalOutcome(BaseModel):
    reason: AgentRunTerminalReason
    status: AgentRunWaitStatus
    error: str | None = None
    stop_reason: str | None = None
    liveness_state: str | None = None
    timeout_phase: str | None = None
    provider_started: bool | None = None
    started_at: int | None = None
    ended_at: int | None = None


def normalize_agent_run_terminal_outcome(raw: dict[str, Any]) -> AgentRunTerminalOutcome:
    status_raw = str(raw.get("status") or "error")
    status = AgentRunWaitStatus(status_raw) if status_raw in AgentRunWaitStatus.__members__.values() else AgentRunWaitStatus.ERROR

    stop_reason = _as_string(raw.get("stopReason"))
    timeout_phase = _as_string(raw.get("timeoutPhase"))
    liveness_state = _as_string(raw.get("livenessState"))

    if status == AgentRunWaitStatus.TIMEOUT and timeout_phase in HARD_TIMEOUT_PHASES:
        reason = AgentRunTerminalReason.HARD_TIMEOUT
    elif status == AgentRunWaitStatus.TIMEOUT:
        reason = AgentRunTerminalReason.TIMED_OUT
    elif stop_reason in {"cancelled", "canceled"}:
        reason = AgentRunTerminalReason.CANCELLED
    elif stop_reason in {"aborted", "restart-abort"}:
        reason = AgentRunTerminalReason.ABORTED
    elif liveness_state == "blocked":
        reason = AgentRunTerminalReason.BLOCKED
    elif status == AgentRunWaitStatus.OK:
        reason = AgentRunTerminalReason.COMPLETED
    else:
        reason = AgentRunTerminalReason.FAILED

    return AgentRunTerminalOutcome(
        reason=reason,
        status=status,
        error=_as_string(raw.get("error")),
        stop_reason=stop_reason,
        liveness_state=liveness_state,
        timeout_phase=timeout_phase,
        provider_started=bool(raw.get("providerStarted")) if raw.get("providerStarted") is not None else None,
        started_at=_as_int(raw.get("startedAt")),
        ended_at=_as_int(raw.get("endedAt")),
    )


def _as_string(value: Any) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


def _as_int(value: Any) -> int | None:
    return value if isinstance(value, int) else None
