from __future__ import annotations

import time
from typing import Any, Optional

from .types import GatewayEvent, JsonObject, OpenClawEvent, OpenClawEventType


def _as_record(value: Any) -> JsonObject:
    if isinstance(value, dict):
        return value
    return {}


def _read_string(value: Any) -> Optional[str]:
    if isinstance(value, str) and len(value) > 0:
        return value
    return None


def _read_number(value: Any) -> Optional[int]:
    if isinstance(value, (int, float)) and value == value:
        return int(value)
    return None


def _read_lower_string(value: Any) -> Optional[str]:
    s = _read_string(value)
    if s is not None:
        return s.lower()
    return None


def _has_hard_timeout_metadata(data: JsonObject, status_already_timeout_attributed: bool = False) -> bool:
    timeout_phase = _read_lower_string(data.get("timeoutPhase"))
    return (
        (status_already_timeout_attributed and data.get("providerStarted") is True)
        or timeout_phase == "preflight"
        or timeout_phase == "provider"
        or timeout_phase == "post_turn"
    )


def _is_lifecycle_cancellation(data: JsonObject) -> bool:
    status = _read_lower_string(data.get("status"))
    stop_reason = _read_lower_string(data.get("stopReason"))
    return (
        status == "aborted"
        or status == "cancelled"
        or status == "canceled"
        or status == "killed"
        or stop_reason == "aborted"
        or stop_reason == "cancelled"
        or stop_reason == "canceled"
        or stop_reason == "killed"
        or stop_reason == "auth-revoked"
        or stop_reason == "restart"
        or stop_reason == "rpc"
        or stop_reason == "user"
        or (data.get("aborted") is True and stop_reason == "stop")
    )


def _normalize_lifecycle_end_event_type(data: JsonObject) -> OpenClawEventType:
    status = _read_lower_string(data.get("status"))
    stop_reason = _read_lower_string(data.get("stopReason"))
    status_already_timeout_attributed = (
        stop_reason != "restart"
        and (status == "timeout" or status == "timed_out" or data.get("aborted") is True)
    )
    if _has_hard_timeout_metadata(data, status_already_timeout_attributed):
        return "run.timed_out"
    if _is_lifecycle_cancellation(data):
        return "run.cancelled"
    if (
        status == "timeout"
        or status == "timed_out"
        or stop_reason == "timeout"
        or stop_reason == "timed_out"
    ):
        return "run.timed_out"
    if data.get("aborted") is True:
        return "run.timed_out"
    return "run.completed"


def _normalize_agent_event_type(payload: JsonObject) -> OpenClawEventType:
    stream = _read_string(payload.get("stream"))
    data = _as_record(payload.get("data"))
    phase = _read_string(data.get("phase"))
    status = _read_string(data.get("status"))

    if stream == "assistant":
        if data.get("delta") is True or isinstance(data.get("delta"), str):
            return "assistant.delta"
        return "assistant.message"
    if stream == "thinking" or stream == "plan":
        return "thinking.delta"
    if stream == "lifecycle":
        if phase == "start":
            return "run.started"
        if phase == "end":
            return _normalize_lifecycle_end_event_type(data)
        if phase == "error":
            if _has_hard_timeout_metadata(data, False):
                return "run.timed_out"
            if _is_lifecycle_cancellation(data):
                return "run.cancelled"
            return "run.failed"
    if stream in ("tool", "item", "command_output"):
        if phase == "start" or status == "running":
            return "tool.call.started"
        if phase == "delta" or phase == "update":
            return "tool.call.delta"
        if status in ("failed", "blocked"):
            return "tool.call.failed"
        if phase == "end" or status == "completed":
            return "tool.call.completed"
        return "tool.call.delta"
    if stream == "approval":
        if phase == "resolved":
            return "approval.resolved"
        return "approval.requested"
    if stream == "patch":
        return "artifact.updated"
    if stream == "error":
        return "run.failed"
    return "raw"


def _normalize_named_event_type(event: GatewayEvent) -> OpenClawEventType:
    payload = _as_record(event.get("payload"))
    event_name = event.get("event", "")

    if event_name == "agent":
        return _normalize_agent_event_type(payload)
    if event_name == "sessions.changed":
        reason = _read_string(payload.get("reason"))
        if reason == "create":
            return "session.created"
        if reason == "compact":
            return "session.compacted"
        return "session.updated"
    if event_name == "session.message":
        return "assistant.message"
    if event_name == "session.tool":
        return "tool.call.delta"
    if event_name in ("exec.approval.requested", "plugin.approval.requested"):
        return "approval.requested"
    if event_name in ("exec.approval.resolved", "plugin.approval.resolved"):
        return "approval.resolved"
    if event_name in ("task.updated", "tasks.changed"):
        return "task.updated"
    return "raw"


def normalize_gateway_event(event: GatewayEvent) -> OpenClawEvent:
    payload = _as_record(event.get("payload"))
    run_id = _read_string(payload.get("runId"))
    session_id = _read_string(payload.get("sessionId"))
    session_key = _read_string(payload.get("sessionKey"))
    task_id = _read_string(payload.get("taskId"))
    agent_id = _read_string(payload.get("agentId"))
    ts = _read_number(payload.get("ts"))
    if ts is None:
        ts = int(time.time.time() * 1000)
    seq = event.get("seq", "local")
    id_parts = [str(seq), event.get("event", ""), run_id or "", session_key or "", str(ts)]
    id_str = ":".join(p for p in id_parts if p)

    result: OpenClawEvent = {
        "version": 1,
        "id": id_str,
        "ts": ts,
        "type": _normalize_named_event_type(event),
        "data": payload.get("data", payload),
        "raw": event,
    }
    if run_id:
        result["runId"] = run_id
    if session_id:
        result["sessionId"] = session_id
    if session_key:
        result["sessionKey"] = session_key
    if task_id:
        result["taskId"] = task_id
    if agent_id:
        result["agentId"] = agent_id
    return result
