"""Resolves retry, fallback, and terminal failover decisions for a run."""

from __future__ import annotations

from typing import Any, Literal, TypedDict

from openclaw.agents.embedded_agent_helpers.types import FailoverReason

RunFailoverAction = Literal[
    "continue_normal",
    "rotate_profile",
    "surface_error",
    "fallback_model",
    "return_error_payload",
]


class RunFailoverDecision(TypedDict, total=False):
    action: RunFailoverAction
    reason: FailoverReason | None


def _should_escalate_retry_limit(reason: FailoverReason | None) -> bool:
    return bool(
        reason
        and reason not in ("timeout", "model_not_found", "format", "session_expired")
    )


def _is_terminal_format_failure(
    *,
    allow_format_retry: bool | None,
    failover_failure: bool,
    failover_reason: FailoverReason | None,
) -> bool:
    return (
        failover_failure
        and failover_reason == "format"
        and allow_format_retry is not True
    )


def _should_rotate_prompt(params: dict[str, Any]) -> bool:
    return bool(
        params.get("failoverFailure")
        and params.get("failoverReason") != "timeout"
        and not _is_terminal_format_failure(
            allow_format_retry=params.get("allowFormatRetry"),
            failover_failure=bool(params.get("failoverFailure")),
            failover_reason=params.get("failoverReason"),
        )
    )


def _is_assistant_timeout_failure(params: dict[str, Any]) -> bool:
    return bool(
        params.get("idleTimedOut")
        or (
            params.get("timedOut")
            and not params.get("timedOutDuringCompaction")
            and not params.get("timedOutDuringToolExecution")
        )
    )


def _is_concrete_non_timeout_assistant_failure(params: dict[str, Any]) -> bool:
    reason = params.get("failoverReason")
    return bool(params.get("failoverFailure") and reason and reason != "timeout")


def _should_rotate_assistant(params: dict[str, Any]) -> bool:
    if _is_terminal_format_failure(
        allow_format_retry=params.get("allowFormatRetry"),
        failover_failure=bool(params.get("failoverFailure")),
        failover_reason=params.get("failoverReason"),
    ):
        return False
    timeout_failure = _is_assistant_timeout_failure(params)
    harness_owned = params.get("harnessOwnsTransport") and (
        timeout_failure or params.get("failoverReason") == "timeout"
    )
    if harness_owned and not _is_concrete_non_timeout_assistant_failure(params):
        return False
    return bool((not params.get("aborted") and params.get("failoverFailure")) or timeout_failure)


def _assistant_fallback_reason(params: dict[str, Any]) -> FailoverReason:
    failover_reason = params.get("failoverReason")
    if params.get("failoverFailure") and failover_reason and failover_reason != "timeout":
        return failover_reason  # type: ignore[return-value]
    if _is_assistant_timeout_failure(params):
        return "timeout"
    return failover_reason or "unknown"  # type: ignore[return-value]


def merge_retry_failover_reason(
    *,
    previous: FailoverReason | None,
    failover_reason: FailoverReason | None,
    timed_out: bool | None = None,
) -> FailoverReason | None:
    if failover_reason is not None:
        return failover_reason
    if timed_out:
        return "timeout"
    return previous


def resolve_run_failover_decision(params: dict[str, Any]) -> RunFailoverDecision:
    stage = params.get("stage")
    if stage == "retry_limit":
        if params.get("fallbackConfigured") and _should_escalate_retry_limit(
            params.get("failoverReason")
        ):
            return {
                "action": "fallback_model",
                "reason": params.get("failoverReason") or "unknown",
            }
        return {"action": "return_error_payload"}

    if stage == "prompt":
        if params.get("externalAbort"):
            return {"action": "surface_error", "reason": params.get("failoverReason")}
        if params.get("harnessOwnsTransport") and params.get("failoverReason") == "timeout":
            return {"action": "surface_error", "reason": params.get("failoverReason")}
        if not params.get("profileRotated") and _should_rotate_prompt(params):
            return {"action": "rotate_profile", "reason": params.get("failoverReason")}
        if params.get("fallbackConfigured") and params.get("failoverFailure") and not _is_terminal_format_failure(
            allow_format_retry=params.get("allowFormatRetry"),
            failover_failure=True,
            failover_reason=params.get("failoverReason"),
        ):
            return {
                "action": "fallback_model",
                "reason": params.get("failoverReason") or "unknown",
            }
        return {"action": "surface_error", "reason": params.get("failoverReason")}

    if stage == "assistant":
        if params.get("externalAbort"):
            return {"action": "surface_error", "reason": params.get("failoverReason")}
        if _is_terminal_format_failure(
            allow_format_retry=params.get("allowFormatRetry"),
            failover_failure=bool(params.get("failoverFailure")),
            failover_reason=params.get("failoverReason"),
        ):
            return {"action": "surface_error", "reason": params.get("failoverReason")}
        assistant_should_rotate = _should_rotate_assistant(params)
        if not params.get("profileRotated") and assistant_should_rotate:
            return {"action": "rotate_profile", "reason": params.get("failoverReason")}
        if assistant_should_rotate and params.get("fallbackConfigured"):
            return {
                "action": "fallback_model",
                "reason": _assistant_fallback_reason(params),
            }
        if not assistant_should_rotate:
            return {"action": "continue_normal"}
        return {"action": "surface_error", "reason": params.get("failoverReason")}

    return {"action": "surface_error", "reason": params.get("failoverReason")}