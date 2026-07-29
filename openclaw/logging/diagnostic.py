"""Diagnostic logger records structured runtime events, timings, and health snapshots.

Mirrors src/logging/diagnostic.ts.
"""

from __future__ import annotations

import threading
import time
from typing import Any

from openclaw.logging.diagnostic_memory import emit_diagnostic_memory_sample, reset_diagnostic_memory_for_test
from openclaw.logging.diagnostic_phase import get_current_diagnostic_phase, get_recent_diagnostic_phases, reset_diagnostic_phases_for_test
from openclaw.logging.diagnostic_run_activity import get_diagnostic_session_activity_snapshot, reset_diagnostic_run_activity_for_test
from openclaw.logging.diagnostic_runtime import diagnostic_logger as _diagnostic_logger, get_last_diagnostic_activity_at, mark_diagnostic_activity, reset_diagnostic_activity_for_test
from openclaw.logging.diagnostic_session_attention import classify_session_attention, is_terminal_diagnostic_progress_reason
from openclaw.logging.diagnostic_session_context import format_cron_session_diagnostic_fields, resolve_cron_session_diagnostic_context
from openclaw.logging.diagnostic_session_recovery_coordinator import (
    request_stuck_session_recovery,
    request_stuck_session_recovery_outcome,
    reset_diagnostic_session_recovery_coordinator_for_test,
)
from openclaw.logging.diagnostic_session_state import (
    diagnostic_session_states,
    get_diagnostic_session_state,
    get_diagnostic_session_state_count_for_test as _get_diagnostic_session_state_count_for_test,
    prune_diagnostic_session_states,
    reset_diagnostic_session_state_for_test,
)
from openclaw.logging.diagnostic_stability import (
    reset_diagnostic_stability_recorder_for_test,
    start_diagnostic_stability_recorder,
    stop_diagnostic_stability_recorder,
)
from openclaw.logging.diagnostic_stability_bundle import (
    install_diagnostic_stability_fatal_hook,
    reset_diagnostic_stability_bundle_for_test,
    uninstall_diagnostic_stability_fatal_hook,
)

diagnostic_logger = _diagnostic_logger
log_lane_enqueue = lambda lane, queue_size: None
log_lane_dequeue = lambda lane, wait_ms, queue_size: None

try:
    from openclaw.logging.diagnostic_runtime import log_lane_enqueue, log_lane_dequeue
except Exception:
    pass

_webhook_stats = {"received": 0, "processed": 0, "errors": 0, "lastReceived": 0}

DEFAULT_STUCK_SESSION_WARN_MS = 120000
MIN_STUCK_SESSION_WARN_MS = 1000
MAX_STUCK_SESSION_WARN_MS = 24 * 60 * 60 * 1000
MIN_STALLED_EMBEDDED_RUN_ABORT_MS = 5 * 60 * 1000
STALLED_EMBEDDED_RUN_ABORT_WARN_MULTIPLIER = 3
RECENT_DIAGNOSTIC_ACTIVITY_MS = 120000

_heartbeat_timer: threading.Timer | None = None
_heartbeat_lock = threading.Lock()


def _now_ms() -> int:
    return int(time.time() * 1000)


def _are_diagnostics_enabled_for_process() -> bool:
    try:
        from openclaw.infra.diagnostic_events import are_diagnostics_enabled_for_process
        return are_diagnostics_enabled_for_process()
    except Exception:
        return False


def _is_diagnostics_enabled(config: Any = None) -> bool:
    try:
        from openclaw.infra.diagnostic_events import is_diagnostics_enabled
        return is_diagnostics_enabled(config)
    except Exception:
        return False


def _emit_diagnostic_event(params: dict[str, Any]) -> None:
    try:
        from openclaw.infra.diagnostic_events import emit_internal_diagnostic_event
        emit_internal_diagnostic_event(params)
    except Exception:
        pass


def _diag() -> dict[str, Any]:
    return _diagnostic_logger()


def _resolve_stalled_embedded_run_abort_ms(stuck_session_warn_ms: int) -> int:
    return max(MIN_STALLED_EMBEDDED_RUN_ABORT_MS, stuck_session_warn_ms * STALLED_EMBEDDED_RUN_ABORT_WARN_MULTIPLIER)


def is_stuck_session_recovery_enabled(config: Any = None) -> bool:
    return _are_diagnostics_enabled_for_process() and _is_diagnostics_enabled(config)


async def request_stuck_diagnostic_session_recovery(params: dict[str, Any]) -> dict[str, Any] | None:
    async def _recover(request: dict[str, Any]) -> dict[str, Any]:
        try:
            from openclaw.logging.diagnostic_stuck_session_recovery import recover_stuck_diagnostic_session
            return await recover_stuck_diagnostic_session(request)
        except Exception as err:
            _diag()["warn"](f"stuck session recovery unavailable: {str(err)}")
            return {
                "status": "failed",
                "action": "none",
                "reason": "exception",
                "sessionId": request.get("sessionId"),
                "sessionKey": request.get("sessionKey"),
                "error": str(err),
            }

    return await request_stuck_session_recovery_outcome({
        "recover": _recover,
        "classification": {
            "eventType": "session.stalled",
            "reason": "visible_reply_wait_timeout",
            "classification": "stalled_agent_run",
            "activeWorkKind": "embedded_run",
            "recoveryEligible": False,
        },
        "request": params,
    })


def resolve_stuck_session_warn_ms(config: Any = None) -> int:
    raw = None
    if config and isinstance(config, dict):
        diag_config = config.get("diagnostics")
        if isinstance(diag_config, dict):
            raw = diag_config.get("stuckSessionWarnMs")
    if not isinstance(raw, (int, float)):
        return DEFAULT_STUCK_SESSION_WARN_MS
    rounded = int(raw)
    if rounded < MIN_STUCK_SESSION_WARN_MS or rounded > MAX_STUCK_SESSION_WARN_MS:
        return DEFAULT_STUCK_SESSION_WARN_MS
    return rounded


def resolve_stuck_session_abort_ms(config: Any, stuck_session_warn_ms: int) -> int:
    raw = None
    if config and isinstance(config, dict):
        diag_config = config.get("diagnostics")
        if isinstance(diag_config, dict):
            raw = diag_config.get("stuckSessionAbortMs")
    if not isinstance(raw, (int, float)):
        return _resolve_stalled_embedded_run_abort_ms(stuck_session_warn_ms)
    rounded = int(raw)
    if rounded <= 0:
        return _resolve_stalled_embedded_run_abort_ms(stuck_session_warn_ms)
    return max(stuck_session_warn_ms, rounded)


def _is_stalled_embedded_run_recovery_eligible(params: dict[str, Any]) -> bool:
    classification = params.get("classification")
    activity = params.get("activity") or {}
    last_progress_age_ms = activity.get("lastProgressAgeMs")
    return (
        classification is not None
        and classification.get("eventType") == "session.stalled"
        and classification.get("classification") == "stalled_agent_run"
        and classification.get("activeWorkKind") == "embedded_run"
        and isinstance(last_progress_age_ms, (int, float))
        and last_progress_age_ms >= params["stuckSessionAbortMs"]
    )


def _is_blocked_tool_call_recovery_eligible(params: dict[str, Any]) -> bool:
    classification = params.get("classification")
    activity = params.get("activity") or {}
    tool_age_ms = activity.get("activeToolAgeMs")
    last_progress_age_ms = activity.get("lastProgressAgeMs")
    return (
        classification is not None
        and classification.get("eventType") == "session.stalled"
        and classification.get("classification") == "blocked_tool_call"
        and classification.get("activeWorkKind") == "tool_call"
        and isinstance(tool_age_ms, (int, float))
        and isinstance(last_progress_age_ms, (int, float))
        and tool_age_ms >= params["stuckSessionAbortMs"]
        and last_progress_age_ms >= params["stuckSessionAbortMs"]
    )


def _is_stalled_model_call_recovery_eligible(params: dict[str, Any]) -> bool:
    classification = params.get("classification")
    activity = params.get("activity") or {}
    last_progress_age_ms = activity.get("lastProgressAgeMs")
    return (
        classification is not None
        and classification.get("eventType") == "session.stalled"
        and classification.get("classification") == "stalled_agent_run"
        and classification.get("activeWorkKind") == "model_call"
        and activity.get("hasActiveEmbeddedRun") is True
        and isinstance(last_progress_age_ms, (int, float))
        and last_progress_age_ms >= params["stuckSessionAbortMs"]
    )


def _is_active_abort_recovery_eligible(params: dict[str, Any]) -> bool:
    return (
        _is_stalled_embedded_run_recovery_eligible(params)
        or _is_blocked_tool_call_recovery_eligible(params)
        or _is_stalled_model_call_recovery_eligible(params)
    )


def _is_idle_queued_recoverable_session_stall(params: dict[str, Any]) -> bool:
    state = params["state"]
    activity = params["activity"]
    has_embedded_owner = (
        activity.get("activeWorkKind") == "embedded_run"
        or activity.get("hasActiveEmbeddedRun") is True
    )
    has_orphaned_activity = (
        activity.get("activeWorkKind") is not None
        and activity.get("hasActiveEmbeddedRun") is not True
    )
    return (
        state.get("state") == "idle"
        and state.get("queueDepth", 0) > 0
        and (has_embedded_owner or has_orphaned_activity)
        and (activity.get("lastProgressAgeMs") or 0) > params["staleMs"]
    )


def log_webhook_received(params: dict[str, Any]) -> None:
    if not _are_diagnostics_enabled_for_process():
        return
    _webhook_stats["received"] += 1
    _webhook_stats["lastReceived"] = _now_ms()
    if _diag().get("isEnabled", lambda level, target="any": False)("debug"):
        _diag()["debug"](
            f"webhook received: channel={params.get('channel')} type={params.get('updateType') or 'unknown'} chatId={params.get('chatId', 'unknown')} total={_webhook_stats['received']}"
        )
    _emit_diagnostic_event({"type": "webhook.received", "channel": params.get("channel"), "updateType": params.get("updateType"), "chatId": params.get("chatId")})
    mark_diagnostic_activity()


def log_webhook_processed(params: dict[str, Any]) -> None:
    if not _are_diagnostics_enabled_for_process():
        return
    _webhook_stats["processed"] += 1
    if _diag().get("isEnabled", lambda level, target="any": False)("debug"):
        _diag()["debug"](
            f"webhook processed: channel={params.get('channel')} type={params.get('updateType') or 'unknown'} chatId={params.get('chatId', 'unknown')} duration={params.get('durationMs', 0)}ms processed={_webhook_stats['processed']}"
        )
    _emit_diagnostic_event({"type": "webhook.processed", "channel": params.get("channel"), "updateType": params.get("updateType"), "chatId": params.get("chatId"), "durationMs": params.get("durationMs")})
    mark_diagnostic_activity()


def log_webhook_error(params: dict[str, Any]) -> None:
    if not _are_diagnostics_enabled_for_process():
        return
    _webhook_stats["errors"] += 1
    _diag()["error"](
        f"webhook error: channel={params.get('channel')} type={params.get('updateType') or 'unknown'} chatId={params.get('chatId', 'unknown')} error=\"{params.get('error', '')}\" errors={_webhook_stats['errors']}"
    )
    _emit_diagnostic_event({"type": "webhook.error", "channel": params.get("channel"), "updateType": params.get("updateType"), "chatId": params.get("chatId"), "error": params.get("error")})
    mark_diagnostic_activity()


def log_message_queued(params: dict[str, Any]) -> None:
    if not _are_diagnostics_enabled_for_process():
        return
    state = get_diagnostic_session_state(params)
    state["queueDepth"] = state.get("queueDepth", 0) + 1
    state["lastActivity"] = _now_ms()
    state["generation"] = (state.get("generation") or 0) + 1
    state["lastStuckWarnAgeMs"] = None
    state["lastLongRunningWarnAgeMs"] = None
    if _diag().get("isEnabled", lambda level, target="any": False)("debug"):
        _diag()["debug"](
            f"message queued: sessionId={state.get('sessionId') or 'unknown'} sessionKey={state.get('sessionKey') or 'unknown'} source={params.get('source')} queueDepth={state['queueDepth']} sessionState={state['state']}"
        )
    _emit_diagnostic_event({"type": "message.queued", "sessionId": state.get("sessionId"), "sessionKey": state.get("sessionKey"), "channel": params.get("channel"), "source": params.get("source"), "queueDepth": state["queueDepth"]})
    mark_diagnostic_activity()


def log_message_received(params: dict[str, Any]) -> None:
    if not _are_diagnostics_enabled_for_process():
        return
    if _diag().get("isEnabled", lambda level, target="any": False)("debug"):
        _diag()["debug"](
            f"message received: channel={params.get('channel') or 'unknown'} chatId={params.get('chatId', 'unknown')} messageId={params.get('messageId', 'unknown')} sessionId={params.get('sessionId') or 'unknown'} sessionKey={params.get('sessionKey') or 'unknown'} source={params.get('source')}"
        )
    _emit_diagnostic_event({"type": "message.received", "sessionId": params.get("sessionId"), "sessionKey": params.get("sessionKey"), "channel": params.get("channel"), "messageId": params.get("messageId"), "chatId": params.get("chatId"), "source": params.get("source")})
    mark_diagnostic_activity()


def log_message_dispatch_started(params: dict[str, Any]) -> None:
    if not _are_diagnostics_enabled_for_process():
        return
    if _diag().get("isEnabled", lambda level, target="any": False)("debug"):
        _diag()["debug"](
            f"message dispatch started: channel={params.get('channel') or 'unknown'} sessionId={params.get('sessionId') or 'unknown'} sessionKey={params.get('sessionKey') or 'unknown'} source={params.get('source')}"
        )
    _emit_diagnostic_event({"type": "message.dispatch.started", "sessionId": params.get("sessionId"), "sessionKey": params.get("sessionKey"), "channel": params.get("channel"), "source": params.get("source")})
    mark_diagnostic_activity()


def log_message_dispatch_completed(params: dict[str, Any]) -> None:
    if not _are_diagnostics_enabled_for_process():
        return
    if params.get("outcome") == "error":
        _diag()["error"](
            f"message dispatch completed: channel={params.get('channel') or 'unknown'} sessionId={params.get('sessionId') or 'unknown'} sessionKey={params.get('sessionKey') or 'unknown'} source={params.get('source')} outcome={params.get('outcome')} duration={params.get('durationMs', 0)}ms{f' reason={params[\"reason\"]}' if params.get('reason') else ''}{f' error=\"{params[\"error\"]}\"' if params.get('error') else ''}"
        )
    elif _diag().get("isEnabled", lambda level, target="any": False)("debug"):
        _diag()["debug"](
            f"message dispatch completed: channel={params.get('channel') or 'unknown'} sessionId={params.get('sessionId') or 'unknown'} sessionKey={params.get('sessionKey') or 'unknown'} source={params.get('source')} outcome={params.get('outcome')} duration={params.get('durationMs', 0)}ms{f' reason={params[\"reason\"]}' if params.get('reason') else ''}{f' error=\"{params[\"error\"]}\"' if params.get('error') else ''}"
        )
    _emit_diagnostic_event({"type": "message.dispatch.completed", "sessionId": params.get("sessionId"), "sessionKey": params.get("sessionKey"), "channel": params.get("channel"), "source": params.get("source"), "durationMs": params.get("durationMs"), "outcome": params.get("outcome"), "reason": params.get("reason"), "error": params.get("error")})
    mark_diagnostic_activity()


def log_message_processed(params: dict[str, Any]) -> None:
    if not _are_diagnostics_enabled_for_process():
        return
    wants_log = params.get("outcome") == "error" or _diag().get("isEnabled", lambda level, target="any": False)("debug")
    if wants_log:
        payload = f"message processed: channel={params.get('channel')} chatId={params.get('chatId', 'unknown')} messageId={params.get('messageId', 'unknown')} sessionId={params.get('sessionId') or 'unknown'} sessionKey={params.get('sessionKey') or 'unknown'} outcome={params.get('outcome')} duration={params.get('durationMs', 0)}ms{f' reason={params[\"reason\"]}' if params.get('reason') else ''}{f' error=\"{params[\"error\"]}\"' if params.get('error') else ''}"
        if params.get("outcome") == "error":
            _diag()["error"](payload)
        else:
            _diag()["debug"](payload)
    _emit_diagnostic_event({"type": "message.processed", "channel": params.get("channel"), "chatId": params.get("chatId"), "messageId": params.get("messageId"), "sessionId": params.get("sessionId"), "sessionKey": params.get("sessionKey"), "durationMs": params.get("durationMs"), "outcome": params.get("outcome"), "reason": params.get("reason"), "error": params.get("error")})
    mark_diagnostic_activity()


def log_session_turn_created(params: dict[str, Any]) -> None:
    if not _are_diagnostics_enabled_for_process():
        return
    if _diag().get("isEnabled", lambda level, target="any": False)("debug"):
        _diag()["debug"](
            f"session turn created: runId={params.get('runId')} sessionId={params.get('sessionId') or 'unknown'} sessionKey={params.get('sessionKey') or 'unknown'} agentId={params.get('agentId') or 'unknown'} channel={params.get('channel') or 'unknown'} trigger={params.get('trigger')}"
        )
    _emit_diagnostic_event({"type": "session.turn.created", "runId": params.get("runId"), "sessionId": params.get("sessionId"), "sessionKey": params.get("sessionKey"), "agentId": params.get("agentId"), "channel": params.get("channel"), "trigger": params.get("trigger")})
    mark_diagnostic_activity()


def log_session_state_change(params: dict[str, Any]) -> None:
    if not _are_diagnostics_enabled_for_process():
        return
    state = get_diagnostic_session_state(params)
    is_probe_session = bool(state.get("sessionId") and state["sessionId"].startswith("probe-"))
    prev_state = state.get("state")
    state["state"] = params.get("state")
    state["lastActivity"] = _now_ms()
    state["generation"] = (state.get("generation") or 0) + 1
    state["lastStuckWarnAgeMs"] = None
    state["lastLongRunningWarnAgeMs"] = None
    if params.get("state") == "processing" and prev_state != "processing":
        state["activeQueuedTurn"] = state.get("queueDepth", 0) > 0
    if params.get("state") == "idle":
        state["queueDepth"] = max(0, state.get("queueDepth", 0) - 1)
        state["activeQueuedTurn"] = False
    if not is_probe_session and _diag().get("isEnabled", lambda level, target="any": False)("debug"):
        _diag()["debug"](
            f"session state: sessionId={state.get('sessionId') or 'unknown'} sessionKey={state.get('sessionKey') or 'unknown'} prev={prev_state} new={params.get('state')} reason=\"{params.get('reason') or ''}\" queueDepth={state.get('queueDepth')}"
        )
    _emit_diagnostic_event({"type": "session.state", "sessionId": state.get("sessionId"), "sessionKey": state.get("sessionKey"), "prevState": prev_state, "state": params.get("state"), "reason": params.get("reason"), "queueDepth": state.get("queueDepth")})
    mark_diagnostic_activity()


def update_diagnostic_session_file(params: dict[str, Any]) -> None:
    if not _are_diagnostics_enabled_for_process():
        return
    state = get_diagnostic_session_state(params)
    session_file = params.get("sessionFile")
    state["sessionFile"] = session_file.strip() if isinstance(session_file, str) and session_file.strip() else None
    mark_diagnostic_activity()


def mark_diagnostic_session_progress(params: dict[str, Any]) -> None:
    if not _are_diagnostics_enabled_for_process():
        return
    state = get_diagnostic_session_state(params)
    state["lastActivity"] = _now_ms()
    state["generation"] = (state.get("generation") or 0) + 1
    state["lastStuckWarnAgeMs"] = None
    state["lastLongRunningWarnAgeMs"] = None
    mark_diagnostic_activity()


def _format_session_activity_log_fields(activity: dict[str, Any]) -> str:
    fields: list[str] = []
    if activity.get("lastProgressReason"):
        fields.append(f"lastProgress={activity['lastProgressReason']}")
    if activity.get("lastProgressAgeMs") is not None:
        fields.append(f"lastProgressAge={round(activity['lastProgressAgeMs'] / 1000)}s")
    if activity.get("activeToolName"):
        fields.append(f"activeTool={activity['activeToolName']}")
    if activity.get("activeToolAgeMs") is not None:
        fields.append(f"activeToolAge={round(activity['activeToolAgeMs'] / 1000)}s")
    if is_terminal_diagnostic_progress_reason(activity.get("lastProgressReason")):
        fields.append("terminalProgressStale=true")
    return " ".join(fields)


def log_session_attention(params: dict[str, Any]) -> dict[str, Any] | None:
    if not _are_diagnostics_enabled_for_process():
        return None
    state = get_diagnostic_session_state(params)
    activity = get_diagnostic_session_activity_snapshot({"sessionId": state.get("sessionId"), "sessionKey": state.get("sessionKey")})
    stuck_session_abort_ms = params.get("abortThresholdMs") or _resolve_stalled_embedded_run_abort_ms(params["thresholdMs"])
    classification = classify_session_attention({
        "state": state.get("state"),
        "queueDepth": state.get("queueDepth", 0),
        "activity": activity,
        "staleMs": params["thresholdMs"],
        "stuckSessionAbortMs": stuck_session_abort_ms,
    })
    recovery_eligible = classification.get("recoveryEligible") or _is_active_abort_recovery_eligible({"classification": classification, "activity": activity, "stuckSessionAbortMs": stuck_session_abort_ms})
    suppress_warning = False
    if classification.get("eventType") == "session.stuck":
        next_warn_age_ms = (
            params["thresholdMs"]
            if state.get("lastStuckWarnAgeMs") is None
            else max(state["lastStuckWarnAgeMs"] + params["thresholdMs"], state["lastStuckWarnAgeMs"] * 2)
        )
        if params["ageMs"] < next_warn_age_ms:
            if not recovery_eligible:
                return None
            suppress_warning = True
        else:
            state["lastStuckWarnAgeMs"] = params["ageMs"]
    if classification.get("eventType") == "session.long_running":
        next_warn_age_ms = (
            params["thresholdMs"]
            if state.get("lastLongRunningWarnAgeMs") is None
            else max(state["lastLongRunningWarnAgeMs"] + params["thresholdMs"], state["lastLongRunningWarnAgeMs"] * 2)
        )
        if params["ageMs"] < next_warn_age_ms:
            if not recovery_eligible:
                return None
            suppress_warning = True
        else:
            state["lastLongRunningWarnAgeMs"] = params["ageMs"]
    if suppress_warning:
        return classification

    label = (
        "stuck session" if classification.get("eventType") == "session.stuck"
        else "stalled session" if classification.get("eventType") == "session.stalled"
        else "long-running session"
    )
    activity_fields = _format_session_activity_log_fields(activity)
    cron_fields = format_cron_session_diagnostic_fields(resolve_cron_session_diagnostic_context({"sessionKey": state.get("sessionKey")}))
    detail_fields = " ".join(f for f in [activity_fields, cron_fields] if f)
    message = (
        f"{label}: sessionId={state.get('sessionId') or 'unknown'} sessionKey={state.get('sessionKey') or 'unknown'} "
        f"state={params.get('state')} age={round(params['ageMs'] / 1000)}s queueDepth={state.get('queueDepth', 0)} "
        f"reason={classification.get('reason')} classification={classification.get('classification')}"
        f"{f' activeWorkKind={classification[\"activeWorkKind\"]}' if classification.get('activeWorkKind') else ''}"
        f"{f' {detail_fields}' if detail_fields else ''}"
        f" recovery={'checking' if recovery_eligible else 'none'}"
    )
    if classification.get("eventType") == "session.long_running" and state.get("queueDepth", 0) <= 0:
        _diag()["debug"](message)
    else:
        _diag()["warn"](message)
    base_event = {
        "sessionId": state.get("sessionId"),
        "sessionKey": state.get("sessionKey"),
        "state": params.get("state"),
        "ageMs": params["ageMs"],
        "queueDepth": state.get("queueDepth"),
        "reason": classification.get("reason"),
    }
    if classification.get("activeWorkKind"):
        base_event["activeWorkKind"] = classification["activeWorkKind"]
    if activity.get("lastProgressAgeMs") is not None:
        base_event["lastProgressAgeMs"] = activity["lastProgressAgeMs"]
    if classification.get("eventType") == "session.long_running":
        _emit_diagnostic_event({"type": "session.long_running", **base_event, "classification": "long_running"})
    elif classification.get("eventType") == "session.stalled":
        _emit_diagnostic_event({"type": "session.stalled", **base_event, "classification": classification.get("classification")})
    else:
        _emit_diagnostic_event({"type": "session.stuck", **base_event, "classification": "stale_session_state"})
    mark_diagnostic_activity()
    return classification


def log_run_attempt(params: dict[str, Any]) -> None:
    if not _are_diagnostics_enabled_for_process():
        return
    _diag()["debug"](
        f"run attempt: sessionId={params.get('sessionId') or 'unknown'} sessionKey={params.get('sessionKey') or 'unknown'} runId={params.get('runId')} attempt={params.get('attempt')}"
    )
    _emit_diagnostic_event({"type": "run.attempt", "sessionId": params.get("sessionId"), "sessionKey": params.get("sessionKey"), "runId": params.get("runId"), "attempt": params.get("attempt")})
    mark_diagnostic_activity()


def log_tool_loop_action(params: dict[str, Any]) -> None:
    if not _are_diagnostics_enabled_for_process():
        return
    payload = (
        f"tool loop: sessionId={params.get('sessionId') or 'unknown'} sessionKey={params.get('sessionKey') or 'unknown'} "
        f"tool={params.get('toolName')} level={params.get('level')} action={params.get('action')} "
        f"detector={params.get('detector')} count={params.get('count')}"
        f"{f' pairedTool={params[\"pairedToolName\"]}' if params.get('pairedToolName') else ''}"
        f" message=\"{params.get('message', '')}\""
    )
    if params.get("level") == "critical":
        _diag()["error"](payload)
    else:
        _diag()["warn"](payload)
    _emit_diagnostic_event({"type": "tool.loop", "sessionId": params.get("sessionId"), "sessionKey": params.get("sessionKey"), "toolName": params.get("toolName"), "level": params.get("level"), "action": params.get("action"), "detector": params.get("detector"), "count": params.get("count"), "message": params.get("message"), "pairedToolName": params.get("pairedToolName")})
    mark_diagnostic_activity()


def log_active_runs() -> None:
    if not _are_diagnostics_enabled_for_process():
        return
    now = _now_ms()
    active_sessions = [
        f"{key}(q={s.get('queueDepth', 0)},age={round((now - s.get('lastActivity', 0)) / 1000)}s)"
        for key, s in diagnostic_session_states.items()
        if s.get("state") == "processing"
    ]
    _diag()["debug"](f"active runs: count={len(active_sessions)} sessions=[{', '.join(active_sessions)}]")
    mark_diagnostic_activity()


def _get_diagnostic_work_snapshot(now: int | None = None) -> dict[str, Any]:
    current = now if now is not None else _now_ms()
    active_count = 0
    waiting_count = 0
    queued_count = 0
    active_labels: list[str] = []
    waiting_labels: list[str] = []
    queued_labels: list[str] = []

    for state in diagnostic_session_states.values():
        if state.get("state") == "processing":
            active_count += 1
            if len(active_labels) < 5:
                label = state.get("sessionKey") or state.get("sessionId") or "unknown"
                age_seconds = round(max(0, current - state.get("lastActivity", 0)) / 1000)
                active_labels.append(f"{label}({state['state']},q={state.get('queueDepth', 0)},age={age_seconds}s)")
        elif state.get("state") == "waiting":
            waiting_count += 1
            if len(waiting_labels) < 5:
                label = state.get("sessionKey") or state.get("sessionId") or "unknown"
                age_seconds = round(max(0, current - state.get("lastActivity", 0)) / 1000)
                waiting_labels.append(f"{label}({state['state']},q={state.get('queueDepth', 0)},age={age_seconds}s)")
        queued_backlog = max(0, state.get("queueDepth", 0) - (1 if state.get("state") == "processing" and state.get("activeQueuedTurn") else 0))
        if queued_backlog > 0:
            if len(queued_labels) < 5:
                label = state.get("sessionKey") or state.get("sessionId") or "unknown"
                age_seconds = round(max(0, current - state.get("lastActivity", 0)) / 1000)
                queued_labels.append(f"{label}({state['state']},q={state.get('queueDepth', 0)},age={age_seconds}s)")
        queued_count += queued_backlog

    return {"activeCount": active_count, "waitingCount": waiting_count, "queuedCount": queued_count, "activeLabels": active_labels, "waitingLabels": waiting_labels, "queuedLabels": queued_labels}


def _has_open_diagnostic_work(snapshot: dict[str, Any]) -> bool:
    return snapshot.get("activeCount", 0) > 0 or snapshot.get("waitingCount", 0) > 0 or snapshot.get("queuedCount", 0) > 0


def _has_recent_diagnostic_activity(now: int) -> bool:
    last_activity_at = get_last_diagnostic_activity_at()
    return last_activity_at > 0 and now - last_activity_at <= RECENT_DIAGNOSTIC_ACTIVITY_MS


def _should_write_critical_memory_pressure_bundle(config: Any = None) -> bool:
    if config and isinstance(config, dict):
        diag_config = config.get("diagnostics")
        if isinstance(diag_config, dict):
            return diag_config.get("memoryPressureSnapshot") is True
    return False


def _resolve_diagnostic_session_store_paths(config: Any = None) -> list[str] | None:
    if not config:
        return None
    try:
        from openclaw.config.sessions.targets import resolve_all_agent_session_store_targets_sync
        paths = [t["storePath"] for t in resolve_all_agent_session_store_targets_sync(config)]
        return paths if paths else None
    except Exception:
        return None


def _heartbeat_tick(config: Any = None, opts: dict[str, Any] | None = None) -> None:
    options = opts or {}
    heartbeat_config = config
    if not heartbeat_config:
        try:
            get_config = options.get("getConfig")
            if get_config:
                heartbeat_config = get_config()
        except Exception:
            heartbeat_config = None
    stuck_session_warn_ms = resolve_stuck_session_warn_ms(heartbeat_config)
    stuck_session_abort_ms = resolve_stuck_session_abort_ms(heartbeat_config, stuck_session_warn_ms)
    now = _now_ms()
    prune_diagnostic_session_states(now, True)
    work = _get_diagnostic_work_snapshot(now)
    should_record_memory_sample = _has_recent_diagnostic_activity(now) or _has_open_diagnostic_work(work)
    if options.get("emitMemorySample"):
        options["emitMemorySample"]({"emitSample": should_record_memory_sample})
    else:
        emit_diagnostic_memory_sample({
            "emitSample": should_record_memory_sample,
            "writeCriticalBundle": _should_write_critical_memory_pressure_bundle(heartbeat_config),
            "resolveSessionStorePaths": lambda: _resolve_diagnostic_session_store_paths(heartbeat_config),
        })
    if not should_record_memory_sample:
        return
    _diag()["debug"](
        f"heartbeat: webhooks={_webhook_stats['received']}/{_webhook_stats['processed']}/{_webhook_stats['errors']} active={work['activeCount']} waiting={work['waitingCount']} queued={work['queuedCount']}"
    )
    _emit_diagnostic_event({
        "type": "diagnostic.heartbeat",
        "webhooks": {"received": _webhook_stats["received"], "processed": _webhook_stats["processed"], "errors": _webhook_stats["errors"]},
        "active": work["activeCount"],
        "waiting": work["waitingCount"],
        "queued": work["queuedCount"],
    })
    for state in diagnostic_session_states.values():
        age_ms = now - state.get("lastActivity", 0)
        activity = get_diagnostic_session_activity_snapshot({"sessionId": state.get("sessionId"), "sessionKey": state.get("sessionKey")})
        idle_queued_recoverable_stall = _is_idle_queued_recoverable_session_stall({"state": state, "activity": activity, "staleMs": stuck_session_warn_ms})
        if (state.get("state") == "processing" and age_ms > stuck_session_warn_ms) or idle_queued_recoverable_stall:
            attention_age_ms = activity.get("lastProgressAgeMs") or age_ms if idle_queued_recoverable_stall else age_ms
            classification = log_session_attention({
                "sessionId": state.get("sessionId"),
                "sessionKey": state.get("sessionKey"),
                "state": state.get("state"),
                "ageMs": attention_age_ms,
                "thresholdMs": stuck_session_warn_ms,
                "abortThresholdMs": stuck_session_abort_ms,
            })
            if classification and classification.get("recoveryEligible"):
                request_stuck_session_recovery({
                    "recover": options.get("recoverStuckSession") or _default_recover_stuck_session,
                    "classification": classification,
                    "request": {
                        "sessionId": state.get("sessionId"),
                        "sessionKey": state.get("sessionKey"),
                        "sessionFile": state.get("sessionFile"),
                        "ageMs": attention_age_ms,
                        "queueDepth": state.get("queueDepth"),
                        "expectedState": state.get("state"),
                        "stateGeneration": state.get("generation"),
                        "staleActiveProgressAbortMs": stuck_session_abort_ms,
                    },
                })
            elif classification and _is_active_abort_recovery_eligible({"classification": classification, "activity": activity, "stuckSessionAbortMs": stuck_session_abort_ms}):
                request_stuck_session_recovery({
                    "recover": options.get("recoverStuckSession") or _default_recover_stuck_session,
                    "classification": classification,
                    "request": {
                        "sessionId": state.get("sessionId"),
                        "sessionKey": state.get("sessionKey"),
                        "sessionFile": state.get("sessionFile"),
                        "ageMs": attention_age_ms,
                        "queueDepth": state.get("queueDepth"),
                        "allowActiveAbort": True,
                        "expectedState": state.get("state"),
                        "stateGeneration": state.get("generation"),
                    },
                })


async def _default_recover_stuck_session(params: dict[str, Any]) -> dict[str, Any]:
    try:
        from openclaw.logging.diagnostic_stuck_session_recovery import recover_stuck_diagnostic_session
        return await recover_stuck_diagnostic_session(params)
    except Exception as err:
        _diag()["warn"](f"stuck session recovery unavailable: {str(err)}")
        return {"status": "failed", "action": "none", "reason": "exception", "sessionId": params.get("sessionId"), "sessionKey": params.get("sessionKey"), "error": str(err)}


def start_diagnostic_heartbeat(config: Any = None, opts: dict[str, Any] | None = None) -> None:
    global _heartbeat_timer
    if not _are_diagnostics_enabled_for_process() or not _is_diagnostics_enabled(config):
        return
    start_diagnostic_stability_recorder()
    install_diagnostic_stability_fatal_hook()
    with _heartbeat_lock:
        if _heartbeat_timer is not None:
            return

        def tick() -> None:
            global _heartbeat_timer
            try:
                _heartbeat_tick(config, opts)
            finally:
                with _heartbeat_lock:
                    if _heartbeat_timer is not None:
                        _heartbeat_timer = threading.Timer(30.0, tick)
                        _heartbeat_timer.daemon = True
                        _heartbeat_timer.start()

        _heartbeat_timer = threading.Timer(30.0, tick)
        _heartbeat_timer.daemon = True
        _heartbeat_timer.start()


def stop_diagnostic_heartbeat() -> None:
    global _heartbeat_timer
    with _heartbeat_lock:
        if _heartbeat_timer is not None:
            _heartbeat_timer.cancel()
            _heartbeat_timer = None
    stop_diagnostic_stability_recorder()
    uninstall_diagnostic_stability_fatal_hook()


def get_diagnostic_session_state_count_for_test() -> int:
    return _get_diagnostic_session_state_count_for_test()


def reset_diagnostic_state_for_test() -> None:
    reset_diagnostic_session_recovery_coordinator_for_test()
    reset_diagnostic_session_state_for_test()
    reset_diagnostic_activity_for_test()
    reset_diagnostic_run_activity_for_test()
    _webhook_stats["received"] = 0
    _webhook_stats["processed"] = 0
    _webhook_stats["errors"] = 0
    _webhook_stats["lastReceived"] = 0
    stop_diagnostic_heartbeat()
    reset_diagnostic_memory_for_test()
    reset_diagnostic_phases_for_test()
    reset_diagnostic_stability_recorder_for_test()
    reset_diagnostic_stability_bundle_for_test()


__all__ = [
    "diagnostic_logger",
    "log_lane_enqueue",
    "log_lane_dequeue",
    "is_stuck_session_recovery_enabled",
    "request_stuck_diagnostic_session_recovery",
    "resolve_stuck_session_warn_ms",
    "resolve_stuck_session_abort_ms",
    "log_webhook_received",
    "log_webhook_processed",
    "log_webhook_error",
    "log_message_queued",
    "log_message_received",
    "log_message_dispatch_started",
    "log_message_dispatch_completed",
    "log_message_processed",
    "log_session_turn_created",
    "log_session_state_change",
    "update_diagnostic_session_file",
    "mark_diagnostic_session_progress",
    "log_session_attention",
    "log_run_attempt",
    "log_tool_loop_action",
    "log_active_runs",
    "start_diagnostic_heartbeat",
    "stop_diagnostic_heartbeat",
    "get_diagnostic_session_state_count_for_test",
    "reset_diagnostic_state_for_test",
]
