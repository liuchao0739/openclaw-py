"""Converts retry-limit exhaustion into failover errors or terminal replies."""

from __future__ import annotations

from typing import Any, TypedDict

from openclaw.agents.embedded_agent_runner.run.failover_policy import RunFailoverDecision
from openclaw.agents.failover_error import FailoverError, resolve_failover_status


class EmbeddedAgentRunResult(TypedDict, total=False):
    payloads: list[dict[str, Any]]
    meta: dict[str, Any]


def handle_retry_limit_exhaustion(
    *,
    message: str,
    decision: RunFailoverDecision,
    provider: str,
    model: str,
    profile_id: str | None = None,
    duration_ms: int,
    agent_meta: dict[str, Any],
    replay_invalid: bool | None = None,
    liveness_state: str | None = None,
) -> EmbeddedAgentRunResult:
    if decision.get("action") == "fallback_model":
        reason = decision.get("reason") or "unknown"
        raise FailoverError(
            message,
            reason=reason,  # type: ignore[arg-type]
            provider=provider,
            model=model,
            profile_id=profile_id,
            status=resolve_failover_status(reason),  # type: ignore[arg-type]
        )

    meta: dict[str, Any] = {
        "durationMs": duration_ms,
        "agentMeta": agent_meta,
        "error": {"kind": "retry_limit", "message": message},
    }
    if replay_invalid:
        meta["replayInvalid"] = True
    if liveness_state:
        meta["livenessState"] = liveness_state

    return {
        "payloads": [
            {
                "text": (
                    "Request failed after repeated internal retries. "
                    "Please try again, or use /new to start a fresh session."
                ),
                "isError": True,
            }
        ],
        "meta": meta,
    }