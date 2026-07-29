"""Stuck session recovery runtime helpers inspect embedded sessions for recovery.

Mirrors src/logging/diagnostic-stuck-session-recovery.runtime.ts.
"""

from __future__ import annotations

from typing import Any

from openclaw.logging.diagnostic_run_activity import get_diagnostic_session_activity_snapshot
from openclaw.logging.diagnostic_session_context import (
    format_stopped_cron_session_diagnostic_fields,
    resolve_cron_session_diagnostic_context,
)
from openclaw.logging.diagnostic_session_recovery import (
    format_recovery_outcome,
    resolve_stuck_session_recovery_ref,
)
from openclaw.logging.diagnostic_session_state import is_diagnostic_session_state_current

STUCK_SESSION_ABORT_SETTLE_MS = 15000
STUCK_SESSION_PROGRESS_STALE_MS = 5 * 60 * 1000
_recoveries_in_flight: set[str] = set()


def _diag() -> dict[str, Any]:
    try:
        from openclaw.logging.diagnostic_runtime import diagnostic_logger
        return diagnostic_logger()
    except Exception:
        return {"warn": lambda msg: None, "debug": lambda msg: None, "error": lambda msg: None}


def _resolve_stale_active_progress_abort_ms(params: dict[str, Any]) -> int:
    configured = params.get("staleActiveProgressAbortMs")
    if isinstance(configured, (int, float)) and configured > 0:
        return int(configured)
    return STUCK_SESSION_PROGRESS_STALE_MS


def _is_active_run_progress_stale(params: dict[str, Any]) -> bool:
    if (params.get("queueDepth") or 0) <= 0:
        return False
    activity = get_diagnostic_session_activity_snapshot({
        "sessionId": params.get("sessionId"),
        "sessionKey": params.get("sessionKey"),
    })
    last_progress_age_ms = activity.get("lastProgressAgeMs")
    return isinstance(last_progress_age_ms, (int, float)) and last_progress_age_ms >= params["staleAbortMs"]


def _format_recovery_context(
    params: dict[str, Any],
    extra: dict[str, Any] | None = None,
) -> str:
    e = extra or {}
    fields = [
        f"sessionId={params.get('sessionId') or e.get('activeSessionId') or 'unknown'}",
        f"sessionKey={params.get('sessionKey') or 'unknown'}",
        f"age={round(params.get('ageMs', 0) / 1000)}s",
        f"queueDepth={params.get('queueDepth') or 0}",
    ]
    if e.get("activeSessionId"):
        fields.append(f"activeSessionId={e['activeSessionId']}")
    if e.get("lane"):
        fields.append(f"lane={e['lane']}")
    if e.get("activeCount") is not None:
        fields.append(f"laneActive={e['activeCount']}")
    if e.get("queuedCount") is not None:
        fields.append(f"laneQueued={e['queuedCount']}")
    return " ".join(fields)


def _is_embedded_agent_run_handle_active(session_id: str) -> bool:
    try:
        from openclaw.agents.embedded_agent_runner.runs import is_embedded_agent_run_handle_active
        return is_embedded_agent_run_handle_active(session_id)
    except Exception:
        return False


def _is_embedded_agent_run_active(session_id: str) -> bool:
    try:
        from openclaw.agents.embedded_agent_runner.runs import is_embedded_agent_run_active
        return is_embedded_agent_run_active(session_id)
    except Exception:
        return False


def _resolve_active_embedded_run_handle_session_id(session_key: str) -> str | None:
    try:
        from openclaw.agents.embedded_agent_runner.runs import resolve_active_embedded_run_handle_session_id
        return resolve_active_embedded_run_handle_session_id(session_key)
    except Exception:
        return None


def _resolve_active_embedded_run_handle_session_id_by_session_file(session_file: str) -> str | None:
    try:
        from openclaw.agents.embedded_agent_runner.runs import resolve_active_embedded_run_handle_session_id_by_session_file
        return resolve_active_embedded_run_handle_session_id_by_session_file(session_file)
    except Exception:
        return None


def _resolve_active_embedded_run_session_id(session_key: str) -> str | None:
    try:
        from openclaw.agents.embedded_agent_runner.runs import resolve_active_embedded_run_session_id
        return resolve_active_embedded_run_session_id(session_key)
    except Exception:
        return None


def _resolve_active_embedded_run_session_id_by_session_file(session_file: str) -> str | None:
    try:
        from openclaw.agents.embedded_agent_runner.runs import resolve_active_embedded_run_session_id_by_session_file
        return resolve_active_embedded_run_session_id_by_session_file(session_file)
    except Exception:
        return None


def _resolve_embedded_session_lane(key: str) -> str | None:
    try:
        from openclaw.agents.embedded_agent_runner.lanes import resolve_embedded_session_lane
        return resolve_embedded_session_lane(key)
    except Exception:
        return None


def _get_command_lane_snapshot(lane: str) -> dict[str, Any]:
    try:
        from openclaw.process.command_queue import get_command_lane_snapshot
        return get_command_lane_snapshot(lane)
    except Exception:
        return {"activeCount": 0, "queuedCount": 0}


def _get_command_lane_active_task_ids(lane: str) -> list[str]:
    try:
        from openclaw.process.command_queue import get_command_lane_active_task_ids
        return list(get_command_lane_active_task_ids(lane))
    except Exception:
        return []


def _reset_command_lane(lane: str) -> int:
    try:
        from openclaw.process.command_queue import reset_command_lane
        return reset_command_lane(lane)
    except Exception:
        return 0


async def _abort_and_drain_embedded_agent_run(params: dict[str, Any]) -> dict[str, Any]:
    try:
        from openclaw.agents.embedded_agent_runner.runs import abort_and_drain_embedded_agent_run
        return await abort_and_drain_embedded_agent_run(params)
    except Exception:
        return {"aborted": False, "drained": False, "forceCleared": False}


async def recover_stuck_diagnostic_session(params: dict[str, Any]) -> dict[str, Any]:
    key = resolve_stuck_session_recovery_ref(params)
    if not key or key in _recoveries_in_flight:
        return {
            "status": "skipped",
            "action": "observe_only",
            "reason": "missing_session_ref" if not key else "already_in_flight",
            "sessionId": params.get("sessionId"),
            "sessionKey": params.get("sessionKey"),
        }
    _recoveries_in_flight.add(key)
    diag = _diag()
    try:
        if not is_diagnostic_session_state_current({
            "sessionId": params.get("sessionId"),
            "sessionKey": params.get("sessionKey"),
            "generation": params.get("stateGeneration"),
            "state": params.get("expectedState") or "processing",
        }):
            return {
                "status": "skipped",
                "action": "observe_only",
                "reason": "stale_session_state",
                "sessionId": params.get("sessionId"),
                "sessionKey": params.get("sessionKey"),
            }

        fallback_active_session_id = (
            params.get("sessionId") if params.get("sessionId") and _is_embedded_agent_run_handle_active(params["sessionId"]) else None
        )
        file_active_session_id = (
            _resolve_active_embedded_run_handle_session_id_by_session_file(params["sessionFile"])
            if params.get("sessionFile") else None
        )
        active_session_id: str | None = None
        if params.get("sessionKey"):
            active_session_id = (
                _resolve_active_embedded_run_handle_session_id(params["sessionKey"])
                or file_active_session_id
                or fallback_active_session_id
            )
        else:
            active_session_id = file_active_session_id or fallback_active_session_id

        file_active_work_session_id = (
            _resolve_active_embedded_run_session_id_by_session_file(params["sessionFile"])
            if params.get("sessionFile") else None
        )
        active_work_session_id: str | None = None
        if params.get("sessionKey"):
            active_work_session_id = (
                _resolve_active_embedded_run_session_id(params["sessionKey"])
                or file_active_work_session_id
                or params.get("sessionId")
            )
        else:
            active_work_session_id = file_active_work_session_id or params.get("sessionId")

        session_lane = _resolve_embedded_session_lane(key) if key else None
        pre_abort_active_task_ids = set(_get_command_lane_active_task_ids(session_lane) if session_lane else [])
        aborted = False
        drained = True
        force_cleared = False
        stale_active_progress_abort_ms = _resolve_stale_active_progress_abort_ms(params)

        if active_session_id:
            reclaim_stale_active_run = (
                params.get("allowActiveAbort") is not True
                and _is_active_run_progress_stale({
                    "sessionId": active_session_id,
                    "sessionKey": params.get("sessionKey"),
                    "queueDepth": params.get("queueDepth"),
                    "staleAbortMs": stale_active_progress_abort_ms,
                })
            )
            if params.get("allowActiveAbort") is not True and not reclaim_stale_active_run:
                outcome = {
                    "status": "skipped",
                    "action": "observe_only",
                    "reason": "active_embedded_run",
                    "sessionId": params.get("sessionId"),
                    "sessionKey": params.get("sessionKey"),
                    "activeSessionId": active_session_id,
                    "activeWorkKind": "embedded_run",
                }
                diag["warn"](f"stuck session recovery skipped: {_format_recovery_context(params, {'activeSessionId': active_session_id})}")
                diag["warn"](f"stuck session recovery outcome: {format_recovery_outcome(outcome)}")
                return outcome
            if reclaim_stale_active_run:
                diag["warn"](f"stuck session recovery reclaiming stale active run: {_format_recovery_context(params, {'activeSessionId': active_session_id})}")
            result = await _abort_and_drain_embedded_agent_run({
                "sessionId": active_session_id,
                "sessionKey": params.get("sessionKey"),
                "settleMs": STUCK_SESSION_ABORT_SETTLE_MS,
                "forceClear": True,
                "reason": "stuck_recovery",
            })
            aborted = result.get("aborted", False)
            drained = result.get("drained", False)
            force_cleared = result.get("forceCleared", False)

        if not active_session_id and active_work_session_id and _is_embedded_agent_run_active(active_work_session_id):
            reclaim_stale_reply_work = (
                params.get("allowActiveAbort") is not True
                and _is_active_run_progress_stale({
                    "sessionId": active_work_session_id,
                    "sessionKey": params.get("sessionKey"),
                    "queueDepth": params.get("queueDepth"),
                    "staleAbortMs": stale_active_progress_abort_ms,
                })
            )
            if params.get("allowActiveAbort") is True or reclaim_stale_reply_work:
                if reclaim_stale_reply_work:
                    diag["warn"](f"stuck session recovery reclaiming stale active reply work: {_format_recovery_context(params, {'activeSessionId': active_work_session_id})}")
                result = await _abort_and_drain_embedded_agent_run({
                    "sessionId": active_work_session_id,
                    "sessionKey": params.get("sessionKey"),
                    "settleMs": STUCK_SESSION_ABORT_SETTLE_MS,
                    "forceClear": True,
                    "reason": "stuck_recovery",
                })
                aborted = result.get("aborted", False)
                drained = result.get("drained", False)
                force_cleared = result.get("forceCleared", False)
                active_session_id = active_work_session_id
            else:
                outcome = {
                    "status": "skipped",
                    "action": "keep_lane",
                    "reason": "active_reply_work",
                    "sessionId": params.get("sessionId"),
                    "sessionKey": params.get("sessionKey"),
                    "activeSessionId": active_work_session_id,
                    "activeWorkKind": "embedded_run",
                }
                diag["warn"](f"stuck session recovery outcome: {format_recovery_outcome(outcome)}")
                return outcome

        if not active_session_id and session_lane:
            lane_snapshot = _get_command_lane_snapshot(session_lane)
            if lane_snapshot.get("activeCount", 0) > 0:
                outcome = {
                    "status": "skipped",
                    "action": "keep_lane",
                    "reason": "active_lane_task",
                    "sessionId": params.get("sessionId"),
                    "sessionKey": params.get("sessionKey"),
                    "lane": session_lane,
                    "activeCount": lane_snapshot.get("activeCount"),
                    "queuedCount": lane_snapshot.get("queuedCount"),
                }
                diag["warn"](f"stuck session recovery outcome: {format_recovery_outcome(outcome)}")
                return outcome

        queued_count = _get_command_lane_snapshot(session_lane).get("queuedCount", 0) if session_lane else 0
        lane_started_fresh_task = bool(
            session_lane is not None
            and any(tid not in pre_abort_active_task_ids for tid in _get_command_lane_active_task_ids(session_lane))
        )
        has_queued_session_work = (params.get("queueDepth") or 0) > 0
        released = (
            _reset_command_lane(session_lane)
            if session_lane
            and not lane_started_fresh_task
            and (queued_count > 0 or has_queued_session_work or not active_session_id or not aborted or not drained)
            else 0
        )

        clear_stale_queued_session = not aborted and released == 0 and (params.get("queueDepth") or 0) > 0

        if aborted or force_cleared or released > 0 or clear_stale_queued_session:
            action = "abort_embedded_run" if aborted or force_cleared else "release_lane"
            stopped_fields = format_stopped_cron_session_diagnostic_fields(
                resolve_cron_session_diagnostic_context({"sessionKey": params.get("sessionKey"), "activeSessionId": active_session_id})
            )
            diag["warn"](
                f"stuck session recovery: sessionId={params.get('sessionId') or active_session_id or 'unknown'} "
                f"sessionKey={params.get('sessionKey') or 'unknown'} "
                f"age={round(params.get('ageMs', 0) / 1000)}s action={action} "
                f"aborted={aborted} drained={drained} released={released}"
                f"{f' {stopped_fields}' if stopped_fields else ''}"
            )
            if aborted or force_cleared:
                outcome = {
                    "status": "aborted",
                    "action": "abort_embedded_run",
                    "sessionId": params.get("sessionId"),
                    "sessionKey": params.get("sessionKey"),
                    "activeSessionId": active_session_id,
                    "activeWorkKind": "embedded_run",
                    "aborted": aborted,
                    "drained": drained,
                    "forceCleared": force_cleared,
                    "released": released,
                    "lane": session_lane,
                }
                if queued_count > 0:
                    outcome["queuedCount"] = queued_count
            else:
                outcome = {
                    "status": "released",
                    "action": "release_lane",
                    "sessionId": params.get("sessionId"),
                    "sessionKey": params.get("sessionKey"),
                    "released": released,
                    "lane": session_lane,
                }
            diag["warn"](f"stuck session recovery outcome: {format_recovery_outcome(outcome)}")
            return outcome

        outcome = {
            "status": "noop",
            "action": "none",
            "reason": "no_active_work",
            "sessionId": params.get("sessionId"),
            "sessionKey": params.get("sessionKey"),
            "lane": session_lane,
        }
        diag["warn"](f"stuck session recovery outcome: {format_recovery_outcome(outcome)}")
        return outcome
    except Exception as err:
        outcome = {
            "status": "failed",
            "action": "none",
            "reason": "exception",
            "sessionId": params.get("sessionId"),
            "sessionKey": params.get("sessionKey"),
            "error": str(err),
        }
        diag["warn"](
            f"stuck session recovery failed: sessionId={params.get('sessionId') or 'unknown'} "
            f"sessionKey={params.get('sessionKey') or 'unknown'} err={str(err)}"
        )
        return outcome
    finally:
        _recoveries_in_flight.discard(key)


def reset_recoveries_in_flight() -> None:
    _recoveries_in_flight.clear()


__all__ = [
    "recover_stuck_diagnostic_session",
    "reset_recoveries_in_flight",
]
