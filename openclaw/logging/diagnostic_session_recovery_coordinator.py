"""Session recovery coordinator orchestrates stuck-session diagnostics.

Mirrors src/logging/diagnostic-session-recovery-coordinator.ts.
"""

from __future__ import annotations

import time
from typing import Any

from openclaw.logging.diagnostic_session_recovery import (
    recovery_outcome_clears_queued_session_state,
    recovery_outcome_mutates_session_state,
    recovery_outcome_released_count,
    resolve_stuck_session_recovery_ref,
)
from openclaw.logging.diagnostic_session_state import (
    get_diagnostic_session_state,
    is_diagnostic_session_state_current,
    peek_diagnostic_session_state,
)

_recovery_requests_in_flight: set[str] = set()


def _emit_diagnostic_event(params: dict[str, Any]) -> None:
    try:
        from openclaw.infra.diagnostic_events import emit_internal_diagnostic_event
        emit_internal_diagnostic_event(params)
    except Exception:
        pass


def _get_internal_diagnostic_event_sequence() -> int:
    try:
        from openclaw.infra.diagnostic_events import get_internal_diagnostic_event_sequence
        return get_internal_diagnostic_event_sequence()
    except Exception:
        return 0


def _get_diagnostic_embedded_run_activity_sequence() -> int:
    try:
        from openclaw.logging.diagnostic_run_activity import get_diagnostic_embedded_run_activity_sequence
        return get_diagnostic_embedded_run_activity_sequence()
    except Exception:
        return 0


def _clear_diagnostic_embedded_run_activity_for_session(params: dict[str, Any]) -> dict[str, Any]:
    try:
        from openclaw.logging.diagnostic_run_activity import clear_diagnostic_embedded_run_activity_for_session
        return clear_diagnostic_embedded_run_activity_for_session(params)
    except Exception:
        return {"blockedByActiveEmbeddedRun": False}


def _mark_activity() -> None:
    try:
        from openclaw.logging.diagnostic_runtime import mark_diagnostic_activity
        mark_diagnostic_activity()
    except Exception:
        pass


def _emit_session_recovery_requested(params: dict[str, Any]) -> None:
    request = params["request"]
    classification = params["classification"]
    _emit_diagnostic_event({
        "type": "session.recovery.requested",
        "sessionId": request.get("sessionId"),
        "sessionKey": request.get("sessionKey"),
        "state": request.get("expectedState") or "processing",
        "stateGeneration": request.get("stateGeneration"),
        "ageMs": request.get("ageMs"),
        "queueDepth": request.get("queueDepth"),
        "reason": classification.get("reason"),
        "activeWorkKind": classification.get("activeWorkKind"),
        "allowActiveAbort": request.get("allowActiveAbort"),
    })


def _emit_session_recovery_completed(params: dict[str, Any]) -> None:
    request = params["request"]
    outcome = params["outcome"]
    _emit_diagnostic_event({
        "type": "session.recovery.completed",
        "sessionId": request.get("sessionId"),
        "sessionKey": request.get("sessionKey"),
        "state": request.get("expectedState") or "processing",
        "stateGeneration": request.get("stateGeneration"),
        "ageMs": request.get("ageMs"),
        "queueDepth": request.get("queueDepth"),
        "activeWorkKind": outcome.get("activeWorkKind"),
        "status": outcome.get("status"),
        "action": outcome.get("action"),
        "outcomeReason": outcome.get("reason"),
        "released": recovery_outcome_released_count(outcome) or None,
        "stale": params.get("stale"),
    })


def _recovery_outcome_has_queued_lane_work(outcome: dict[str, Any]) -> bool:
    return outcome.get("status") == "aborted" and (outcome.get("queuedCount") or 0) > 0


def _apply_recovery_outcome_to_diagnostic_state(params: dict[str, Any]) -> None:
    outcome = params.get("outcome")
    if not outcome:
        return
    request = params["request"]
    if not recovery_outcome_mutates_session_state(outcome):
        _emit_session_recovery_completed({"request": request, "outcome": outcome})
        return
    expected_state = request.get("expectedState") or "processing"
    current_state = peek_diagnostic_session_state(request)
    current_generation = current_state.get("generation", 0) if current_state else 0
    request_generation = request.get("stateGeneration", 0)
    state_is_current = (
        expected_state == "idle"
        and request.get("stateGeneration") is not None
        and outcome.get("action") == "abort_embedded_run"
    )
    if state_is_current:
        state_is_current = (
            current_state is not None
            and current_state.get("state") == "idle"
            and (current_generation == request_generation or current_generation == request_generation + 1)
        )
    else:
        state_is_current = is_diagnostic_session_state_current({
            "sessionId": request.get("sessionId"),
            "sessionKey": request.get("sessionKey"),
            "generation": request.get("stateGeneration"),
            "state": expected_state,
        })
    if not state_is_current:
        _emit_session_recovery_completed({"request": request, "outcome": outcome, "stale": True})
        return
    state = get_diagnostic_session_state(request)
    activity_clear = _clear_diagnostic_embedded_run_activity_for_session({
        "sessionId": state.get("sessionId"),
        "sessionKey": state.get("sessionKey"),
        "activeSessionId": outcome.get("activeSessionId"),
        "recoveryStartedAfterEmbeddedRunSequence": params.get("recoveryStartedAfterEmbeddedRunSequence"),
        "recoveryStartedAfterDiagnosticEventSequence": params.get("recoveryStartedAfterDiagnosticEventSequence"),
    })
    if activity_clear.get("blockedByActiveEmbeddedRun"):
        _emit_session_recovery_completed({"request": request, "outcome": outcome, "stale": True})
        return
    prev_state = state.get("state")
    state["state"] = "idle"
    state["lastActivity"] = int(time.time() * 1000)
    state["generation"] = (state.get("generation") or 0) + 1
    state["lastStuckWarnAgeMs"] = None
    state["lastLongRunningWarnAgeMs"] = None
    preserve_queued_idle_work = (
        request.get("expectedState") == "idle" and _recovery_outcome_has_queued_lane_work(outcome)
    )
    if recovery_outcome_clears_queued_session_state(outcome):
        state["queueDepth"] = 0
    elif preserve_queued_idle_work:
        state["queueDepth"] = max(state.get("queueDepth", 0), request.get("queueDepth") or 0)
    else:
        state["queueDepth"] = max(0, state.get("queueDepth", 0) - 1)
    _emit_diagnostic_event({
        "type": "session.state",
        "sessionId": state.get("sessionId"),
        "sessionKey": state.get("sessionKey"),
        "prevState": prev_state,
        "state": "idle",
        "reason": f"stuck_recovery:{outcome.get('status')}",
        "queueDepth": state.get("queueDepth"),
    })
    _emit_session_recovery_completed({"request": request, "outcome": outcome})
    _mark_activity()


def request_stuck_session_recovery_outcome(params: dict[str, Any]) -> Any:
    request = params["request"]
    classification = params["classification"]
    recover = params["recover"]
    in_flight_key = resolve_stuck_session_recovery_ref(request)
    if in_flight_key and in_flight_key in _recovery_requests_in_flight:
        outcome: dict[str, Any] = {
            "status": "skipped",
            "action": "observe_only",
            "reason": "already_in_flight",
            "sessionId": request.get("sessionId"),
            "sessionKey": request.get("sessionKey"),
            "activeWorkKind": classification.get("activeWorkKind"),
        }
        _emit_session_recovery_completed({"request": request, "outcome": outcome})
        return outcome
    if in_flight_key:
        _recovery_requests_in_flight.add(in_flight_key)
    _emit_session_recovery_requested({"request": request, "classification": classification})
    recovery_started_after_embedded_run_sequence = _get_diagnostic_embedded_run_activity_sequence()
    recovery_started_after_diagnostic_event_sequence = _get_internal_diagnostic_event_sequence()

    def complete_recovery(outcome: dict[str, Any] | None) -> dict[str, Any] | None:
        _apply_recovery_outcome_to_diagnostic_state({
            "request": request,
            "outcome": outcome,
            "recoveryStartedAfterEmbeddedRunSequence": recovery_started_after_embedded_run_sequence,
            "recoveryStartedAfterDiagnosticEventSequence": recovery_started_after_diagnostic_event_sequence,
        })
        return outcome

    def fail_recovery(err: Any) -> dict[str, Any]:
        outcome = {
            "status": "failed",
            "action": "none",
            "reason": "exception",
            "sessionId": request.get("sessionId"),
            "sessionKey": request.get("sessionKey"),
            "error": str(err),
        }
        _apply_recovery_outcome_to_diagnostic_state({
            "request": request,
            "outcome": outcome,
            "recoveryStartedAfterEmbeddedRunSequence": recovery_started_after_embedded_run_sequence,
            "recoveryStartedAfterDiagnosticEventSequence": recovery_started_after_diagnostic_event_sequence,
        })
        return outcome

    try:
        result = recover(request)
        if hasattr(result, "__await__"):
            async def _async():
                try:
                    outcome = await result
                    return complete_recovery(outcome)
                except Exception as err:
                    return fail_recovery(err)
                finally:
                    if in_flight_key:
                        _recovery_requests_in_flight.discard(in_flight_key)
            return _async()
        outcome = complete_recovery(result)
        if in_flight_key:
            _recovery_requests_in_flight.discard(in_flight_key)
        return outcome
    except Exception as err:
        if in_flight_key:
            _recovery_requests_in_flight.discard(in_flight_key)
        return fail_recovery(err)


def request_stuck_session_recovery(params: dict[str, Any]) -> None:
    request_stuck_session_recovery_outcome(params)


def reset_diagnostic_session_recovery_coordinator_for_test() -> None:
    _recovery_requests_in_flight.clear()


__all__ = [
    "request_stuck_session_recovery_outcome",
    "request_stuck_session_recovery",
    "reset_diagnostic_session_recovery_coordinator_for_test",
]
