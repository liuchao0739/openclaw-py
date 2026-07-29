"""Diagnostic stability helpers compare diagnostic outputs across runs.

Mirrors src/logging/diagnostic-stability.ts.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

DEFAULT_DIAGNOSTIC_STABILITY_CAPACITY = 1000
DEFAULT_DIAGNOSTIC_STABILITY_LIMIT = 50
MAX_DIAGNOSTIC_STABILITY_LIMIT = DEFAULT_DIAGNOSTIC_STABILITY_CAPACITY
LIVENESS_EVENT_LOOP_DELAY_WARN_MS = 1000

SAFE_REASON_CODE = re.compile(r"^[A-Za-z0-9_.:-]{1,120}$", re.UNICODE)


def _get_diagnostic_stability_state() -> dict[str, Any]:
    global_state = globals()
    state = global_state.get("_stability_state")
    if state is None:
        state = {
            "records": [None] * DEFAULT_DIAGNOSTIC_STABILITY_CAPACITY,
            "capacity": DEFAULT_DIAGNOSTIC_STABILITY_CAPACITY,
            "nextIndex": 0,
            "count": 0,
            "dropped": 0,
            "unsubscribe": None,
        }
        global_state["_stability_state"] = state
    return state


def _copy_reason_code(reason: str | None) -> str | None:
    if not reason or not SAFE_REASON_CODE.match(reason):
        return None
    return reason


def _assign_reason_code(record: dict[str, Any], reason: str | None) -> None:
    reason_code = _copy_reason_code(reason)
    if reason_code:
        record["reason"] = reason_code


def _sanitize_diagnostic_event(event: dict[str, Any]) -> dict[str, Any]:
    record: dict[str, Any] = {
        "seq": event.get("seq"),
        "ts": event.get("ts"),
        "type": event.get("type"),
    }
    event_type = event.get("type", "")

    if event_type == "model.usage":
        record["channel"] = event.get("channel")
        record["provider"] = event.get("provider")
        record["model"] = event.get("model")
        record["usage"] = dict(event.get("usage") or {})
        record["context"] = dict(event["context"]) if event.get("context") else None
        record["costUsd"] = event.get("costUsd")
        record["durationMs"] = event.get("durationMs")
    elif event_type == "webhook.received":
        record["channel"] = event.get("channel")
    elif event_type == "webhook.processed":
        record["channel"] = event.get("channel")
        record["durationMs"] = event.get("durationMs")
    elif event_type == "webhook.error":
        record["channel"] = event.get("channel")
    elif event_type == "message.queued":
        record["channel"] = event.get("channel")
        record["source"] = event.get("source")
        record["queueDepth"] = event.get("queueDepth")
    elif event_type == "message.received":
        record["channel"] = event.get("channel")
        record["source"] = event.get("source")
    elif event_type == "message.dispatch.started":
        record["channel"] = event.get("channel")
        record["source"] = event.get("source")
    elif event_type == "message.dispatch.completed":
        record["channel"] = event.get("channel")
        record["source"] = event.get("source")
        record["durationMs"] = event.get("durationMs")
        record["outcome"] = event.get("outcome")
        _assign_reason_code(record, event.get("reason"))
    elif event_type == "message.processed":
        record["channel"] = event.get("channel")
        record["durationMs"] = event.get("durationMs")
        record["outcome"] = event.get("outcome")
        _assign_reason_code(record, event.get("reason"))
    elif event_type == "message.delivery.started":
        record["channel"] = event.get("channel")
        record["deliveryKind"] = event.get("deliveryKind")
    elif event_type == "message.delivery.completed":
        record["channel"] = event.get("channel")
        record["deliveryKind"] = event.get("deliveryKind")
        record["durationMs"] = event.get("durationMs")
        record["resultCount"] = event.get("resultCount")
        record["outcome"] = "completed"
    elif event_type == "message.delivery.error":
        record["channel"] = event.get("channel")
        record["deliveryKind"] = event.get("deliveryKind")
        record["durationMs"] = event.get("durationMs")
        record["outcome"] = "error"
        _assign_reason_code(record, event.get("errorCategory"))
    elif event_type == "session.state":
        record["outcome"] = event.get("state")
        _assign_reason_code(record, event.get("reason"))
        record["queueDepth"] = event.get("queueDepth")
    elif event_type in ("session.long_running", "session.stalled", "session.stuck"):
        record["outcome"] = event.get("state")
        if event_type == "session.stuck":
            record["level"] = "warning"
        _assign_reason_code(record, event.get("reason"))
        record["ageMs"] = event.get("ageMs")
        record["queueDepth"] = event.get("queueDepth")
        if event.get("activeWorkKind"):
            record["activeWorkKind"] = event.get("activeWorkKind")
    elif event_type == "session.recovery.requested":
        record["outcome"] = event.get("state")
        record["action"] = "abort" if event.get("allowActiveAbort") else "recover"
        record["ageMs"] = event.get("ageMs")
        record["queueDepth"] = event.get("queueDepth")
        if event.get("activeWorkKind"):
            record["activeWorkKind"] = event.get("activeWorkKind")
        _assign_reason_code(record, event.get("reason"))
    elif event_type == "session.recovery.completed":
        record["outcome"] = event.get("status")
        record["action"] = event.get("action")
        record["ageMs"] = event.get("ageMs")
        record["queueDepth"] = event.get("queueDepth")
        record["count"] = event.get("released")
        if event.get("activeWorkKind"):
            record["activeWorkKind"] = event.get("activeWorkKind")
        _assign_reason_code(record, event.get("outcomeReason") or event.get("reason"))
    elif event_type == "queue.lane.enqueue":
        record["source"] = event.get("lane")
        record["queueSize"] = event.get("queueSize")
    elif event_type == "queue.lane.dequeue":
        record["source"] = event.get("lane")
        record["queueSize"] = event.get("queueSize")
        record["waitMs"] = event.get("waitMs")
    elif event_type == "run.attempt":
        record["count"] = event.get("attempt")
    elif event_type == "run.progress":
        _assign_reason_code(record, event.get("reason"))
    elif event_type == "tool.execution.started":
        record["toolName"] = event.get("toolName")
        record["source"] = event.get("toolSource")
        record["pluginId"] = event.get("toolOwner")
    elif event_type == "tool.execution.completed":
        record["toolName"] = event.get("toolName")
        record["source"] = event.get("toolSource")
        record["pluginId"] = event.get("toolOwner")
        record["durationMs"] = event.get("durationMs")
    elif event_type == "tool.execution.error":
        record["toolName"] = event.get("toolName")
        record["source"] = event.get("toolSource")
        record["pluginId"] = event.get("toolOwner")
        record["durationMs"] = event.get("durationMs")
        _assign_reason_code(record, event.get("errorCategory"))
    elif event_type == "run.started":
        record["provider"] = event.get("provider")
        record["model"] = event.get("model")
        record["channel"] = event.get("channel")
    elif event_type == "run.completed":
        record["provider"] = event.get("provider")
        record["model"] = event.get("model")
        record["channel"] = event.get("channel")
        record["durationMs"] = event.get("durationMs")
        record["outcome"] = event.get("outcome")
        _assign_reason_code(record, event.get("errorCategory"))
    elif event_type == "model.call.started":
        record["provider"] = event.get("provider")
        record["model"] = event.get("model")
    elif event_type == "model.call.completed":
        record["provider"] = event.get("provider")
        record["model"] = event.get("model")
        record["durationMs"] = event.get("durationMs")
        record["requestBytes"] = event.get("requestPayloadBytes")
        record["responseBytes"] = event.get("responseStreamBytes")
        record["timeToFirstByteMs"] = event.get("timeToFirstByteMs")
    elif event_type == "model.call.error":
        record["provider"] = event.get("provider")
        record["model"] = event.get("model")
        record["durationMs"] = event.get("durationMs")
        record["requestBytes"] = event.get("requestPayloadBytes")
        record["responseBytes"] = event.get("responseStreamBytes")
        record["timeToFirstByteMs"] = event.get("timeToFirstByteMs")
        record["failureKind"] = event.get("failureKind")
        _assign_reason_code(record, event.get("errorCategory"))
    elif event_type == "diagnostic.memory.sample":
        if event.get("memory"):
            record["memory"] = dict(event["memory"])
    elif event_type == "diagnostic.memory.pressure":
        record["level"] = event.get("level")
        _assign_reason_code(record, event.get("reason"))
        if event.get("memory"):
            record["memory"] = dict(event["memory"])
        record["thresholdBytes"] = event.get("thresholdBytes")
        record["rssGrowthBytes"] = event.get("rssGrowthBytes")
        record["windowMs"] = event.get("windowMs")
    elif event_type == "diagnostic.heartbeat":
        record["webhooks"] = dict(event.get("webhooks") or {})
        record["active"] = event.get("active")
        record["waiting"] = event.get("waiting")
        record["queued"] = event.get("queued")
    elif event_type == "diagnostic.liveness.warning":
        record["level"] = "warning"
        record["durationMs"] = event.get("intervalMs")
        record["count"] = len(event.get("reasons") or [])
        reasons = event.get("reasons") or []
        if reasons:
            _assign_reason_code(record, reasons[0])
        record["eventLoopDelayP99Ms"] = event.get("eventLoopDelayP99Ms")
        record["eventLoopDelayMaxMs"] = event.get("eventLoopDelayMaxMs")
        record["eventLoopUtilization"] = event.get("eventLoopUtilization")
        record["cpuCoreRatio"] = event.get("cpuCoreRatio")
        record["active"] = event.get("active")
        record["waiting"] = event.get("waiting")
        record["queued"] = event.get("queued")
        record["phase"] = event.get("phase")
    elif event_type == "diagnostic.phase.completed":
        record["phase"] = event.get("name")
        record["durationMs"] = event.get("durationMs")
        record["cpuCoreRatio"] = event.get("cpuCoreRatio")
    elif event_type == "tool.loop":
        record["toolName"] = event.get("toolName")
        record["level"] = event.get("level")
        record["action"] = event.get("action")
        record["detector"] = event.get("detector")
        record["count"] = event.get("count")
        record["pairedToolName"] = event.get("pairedToolName")
    elif event_type == "log.record":
        record["level"] = event.get("level")
        record["source"] = event.get("loggerName")

    return record


def _append_record(record: dict[str, Any]) -> None:
    state = _get_diagnostic_stability_state()
    state["records"][state["nextIndex"]] = record
    state["nextIndex"] = (state["nextIndex"] + 1) % state["capacity"]
    if state["count"] < state["capacity"]:
        state["count"] += 1
        return
    state["dropped"] += 1


def _list_records() -> list[dict[str, Any]]:
    state = _get_diagnostic_stability_state()
    if state["count"] == 0:
        return []
    if state["count"] < state["capacity"]:
        return [r for r in state["records"][:state["count"]] if r is not None]
    return [r for r in state["records"][state["nextIndex"]:] + state["records"][:state["nextIndex"]] if r is not None]


def _summarize_records(records: list[dict[str, Any]]) -> dict[str, Any]:
    by_type: dict[str, int] = {}
    latest_memory: dict[str, Any] | None = None
    max_rss_bytes: int | None = None
    max_heap_used_bytes: int | None = None
    pressure_count = 0
    payload_large = {"count": 0, "rejected": 0, "truncated": 0, "chunked": 0, "bySurface": {}}

    for record in records:
        by_type[record["type"]] = by_type.get(record["type"], 0) + 1
        if record.get("memory"):
            latest_memory = record["memory"]
            rss = latest_memory.get("rssBytes", 0)
            max_rss_bytes = rss if max_rss_bytes is None else max(max_rss_bytes, rss)
            heap = latest_memory.get("heapUsedBytes", 0)
            max_heap_used_bytes = heap if max_heap_used_bytes is None else max(max_heap_used_bytes, heap)
        if record["type"] == "diagnostic.memory.pressure":
            pressure_count += 1
        if record["type"] == "payload.large":
            payload_large["count"] += 1
            action = record.get("action")
            if action == "rejected":
                payload_large["rejected"] += 1
            elif action == "truncated":
                payload_large["truncated"] += 1
            elif action == "chunked":
                payload_large["chunked"] += 1
            surface = record.get("surface") or "unknown"
            payload_large["bySurface"][surface] = payload_large["bySurface"].get(surface, 0) + 1

    summary: dict[str, Any] = {"byType": by_type}
    if latest_memory or pressure_count > 0:
        summary["memory"] = {
            "latest": latest_memory,
            "maxRssBytes": max_rss_bytes,
            "maxHeapUsedBytes": max_heap_used_bytes,
            "pressureCount": pressure_count,
        }
    if payload_large["count"] > 0:
        summary["payloadLarge"] = payload_large
    return summary


def _parse_optional_non_negative_integer(value: Any, field: str) -> int | None:
    if value is None or value == "":
        return None
    try:
        parsed = int(value) if not isinstance(value, bool) else None
    except (TypeError, ValueError):
        raise ValueError(f"{field} must be a non-negative integer")
    if parsed is None or parsed < 0:
        raise ValueError(f"{field} must be a non-negative integer")
    return parsed


def _parse_optional_type(value: Any) -> str | None:
    if value is None or value == "":
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError("type must be a non-empty string")
    return value.strip()


def _normalize_limit(limit: Any, default_limit: int = DEFAULT_DIAGNOSTIC_STABILITY_LIMIT) -> int:
    parsed = _parse_optional_non_negative_integer(limit, "limit")
    if parsed is None:
        return default_limit
    if parsed < 1 or parsed > MAX_DIAGNOSTIC_STABILITY_LIMIT:
        raise ValueError(f"limit must be between 1 and {MAX_DIAGNOSTIC_STABILITY_LIMIT}")
    return parsed


def normalize_diagnostic_stability_query(
    input_data: dict[str, Any] | None = None,
    options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    data = input_data or {}
    opts = options or {}
    return {
        "limit": _normalize_limit(data.get("limit"), opts.get("defaultLimit")),
        "type": _parse_optional_type(data.get("type")),
        "sinceSeq": _parse_optional_non_negative_integer(data.get("sinceSeq"), "sinceSeq"),
    }


def _select_records(
    records: list[dict[str, Any]],
    options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    opts = options or {}
    limit = opts.get("limit") if opts.get("limit") is not None else DEFAULT_DIAGNOSTIC_STABILITY_LIMIT
    type_filter = opts.get("type")
    since_seq = opts.get("sinceSeq")
    filtered = [
        record for record in records
        if (not type_filter or record.get("type") == type_filter)
        and (since_seq is None or record.get("seq", 0) > since_seq)
    ]
    return {"filtered": filtered, "events": filtered[max(0, len(filtered) - limit):]}


def start_diagnostic_stability_recorder() -> None:
    state = _get_diagnostic_stability_state()
    if state.get("unsubscribe"):
        return
    try:
        from openclaw.infra.diagnostic_events import on_diagnostic_event
        def handler(event: dict[str, Any]) -> None:
            _append_record(_sanitize_diagnostic_event(event))
        state["unsubscribe"] = on_diagnostic_event(handler)
    except Exception:
        pass


def stop_diagnostic_stability_recorder() -> None:
    state = _get_diagnostic_stability_state()
    if state.get("unsubscribe"):
        try:
            state["unsubscribe"]()
        except Exception:
            pass
    state["unsubscribe"] = None


def get_diagnostic_stability_snapshot(options: dict[str, Any] | None = None) -> dict[str, Any]:
    state = _get_diagnostic_stability_state()
    opts = options or {}
    selection = _select_records(_list_records(), opts)
    filtered = selection["filtered"]
    return {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "capacity": state["capacity"],
        "count": len(filtered),
        "dropped": state["dropped"],
        "firstSeq": filtered[0].get("seq") if filtered else None,
        "lastSeq": filtered[-1].get("seq") if filtered else None,
        "events": selection["events"],
        "summary": _summarize_records(filtered),
    }


def select_diagnostic_stability_snapshot(
    snapshot: dict[str, Any],
    options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    opts = options or {}
    selection = _select_records(snapshot.get("events", []), opts)
    filtered = selection["filtered"]
    return {
        **snapshot,
        "count": len(filtered),
        "firstSeq": filtered[0].get("seq") if filtered else None,
        "lastSeq": filtered[-1].get("seq") if filtered else None,
        "events": selection["events"],
        "summary": _summarize_records(filtered),
    }


def reset_diagnostic_stability_recorder_for_test() -> None:
    global _stability_state
    state = _get_diagnostic_stability_state()
    if state.get("unsubscribe"):
        try:
            state["unsubscribe"]()
        except Exception:
            pass
    _stability_state = None


__all__ = [
    "MAX_DIAGNOSTIC_STABILITY_LIMIT",
    "normalize_diagnostic_stability_query",
    "start_diagnostic_stability_recorder",
    "stop_diagnostic_stability_recorder",
    "get_diagnostic_stability_snapshot",
    "select_diagnostic_stability_snapshot",
    "reset_diagnostic_stability_recorder_for_test",
]
