from __future__ import annotations

import re
from collections.abc import Callable
from typing import Any

from openclaw.plugin_sdk.diagnostic_runtime import (
    DiagnosticEventMetadata,
    DiagnosticEventPayload,
    is_internal_diagnostic_event_metadata,
)
from openclaw.plugin_sdk.plugin_entry import (
    OpenClawPluginHttpRouteHandler,
    OpenClawPluginService,
    OpenClawPluginServiceContext,
)
from openclaw.plugin_sdk.security_runtime import redact_sensitive_text

DURATION_BUCKETS_SECONDS = [
    0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30, 60, 120, 300, 600,
]
TOKEN_BUCKETS = [1, 4, 16, 64, 256, 1024, 4096, 16384, 65536, 262144, 1048576]
BYTE_BUCKETS = [
    1024, 4096, 16384, 65536, 262144, 1048576, 4194304, 16777216, 67108864, 268435456, 1073741824,
    4294967296, 17179869184,
]
RATIO_BUCKETS = [0.01, 0.05, 0.1, 0.25, 0.5, 0.75, 1, 2, 4, 8, 16]
LOW_CARDINALITY_VALUE_RE = re.compile(r'^[A-Za-z0-9_.:-]{1,120}$')
MAX_PROMETHEUS_SERIES = 2048
DROPPED_SERIES_COUNTER_NAME = "openclaw_prometheus_series_dropped_total"


def _low_cardinality_label(value: str | None, fallback: str = "unknown") -> str:
    if not value:
        return fallback
    redacted = redact_sensitive_text(value.strip())
    lowered = redacted.lower()
    if lowered.startswith("agent:") or ":agent:" in lowered:
        return fallback
    return redacted if LOW_CARDINALITY_VALUE_RE.match(redacted) else fallback


def _low_cardinality_queue_lane_label(value: str | None, fallback: str = "unknown") -> str:
    if not value:
        return fallback
    redacted = redact_sensitive_text(value.strip())
    lowered = redacted.lower()
    if lowered.startswith("agent:"):
        return fallback
    scoped_index = redacted.find(":")
    lane = redacted[:scoped_index] if scoped_index >= 0 else redacted
    return lane if LOW_CARDINALITY_VALUE_RE.match(lane) else fallback


def _numeric_value(value: int | float | None) -> int | float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        import math
        if math.isfinite(value) and value >= 0:
            return value
    return None


def _seconds(ms: int | float | None) -> float | None:
    value = _numeric_value(ms)
    if value is None:
        return None
    return value / 1000


def _sorted_labels(labels: dict[str, str]) -> list[tuple[str, str]]:
    return sorted(labels.items(), key=lambda x: x[0])


def _metric_key(name: str, labels: dict[str, str]) -> str:
    import json
    return f"{name}|{json.dumps(_sorted_labels(labels))}"


def _escape_help(value: str) -> str:
    return value.replace("\\", "\\\\").replace("\n", "\\n")


def _escape_label_value(value: str) -> str:
    return value.replace("\\", "\\\\").replace("\n", "\\n").replace('"', '\\"')


def _format_labels(labels: dict[str, str]) -> str:
    entries = _sorted_labels(labels)
    if not entries:
        return ""
    return "{" + ",".join(f'{k}="{_escape_label_value(v)}"' for k, v in entries) + "}"


def _format_prometheus_number(value: int | float) -> str:
    import math
    if not math.isfinite(value):
        return "0"
    if isinstance(value, int) or (isinstance(value, float) and value == int(value)):
        return str(int(value))
    return f"{value:.12g}"


def create_prometheus_metric_store() -> dict[str, Any]:
    counters: dict[str, dict[str, Any]] = {}
    gauges: dict[str, dict[str, Any]] = {}
    histograms: dict[str, dict[str, Any]] = {}
    dropped_series = 0

    def _can_create_series(store: dict[str, Any], key: str, metric_name: str) -> bool:
        nonlocal dropped_series
        if key in store:
            return True
        if metric_name == DROPPED_SERIES_COUNTER_NAME:
            return True
        if len(counters) + len(gauges) + len(histograms) < MAX_PROMETHEUS_SERIES:
            return True
        dropped_series += 1
        return False

    def counter(name: str, help_text: str, labels: dict[str, str], amount: int | float = 1) -> None:
        nonlocal dropped_series
        import math
        if not math.isfinite(amount) or amount <= 0:
            return
        key = _metric_key(name, labels)
        if not _can_create_series(counters, key, name):
            return
        existing = counters.get(key)
        if existing is not None:
            existing["value"] += amount
            return
        counters[key] = {"help": help_text, "labels": dict(labels), "value": amount}

    def gauge(name: str, help_text: str, labels: dict[str, str], value: int | float | None) -> None:
        if value is None:
            return
        key = _metric_key(name, labels)
        if not _can_create_series(gauges, key, name):
            return
        gauges[key] = {"help": help_text, "labels": dict(labels), "value": value}

    def histogram(
        name: str,
        help_text: str,
        labels: dict[str, str],
        value: int | float | None,
        buckets: list[float] | None = None,
    ) -> None:
        if buckets is None:
            buckets = DURATION_BUCKETS_SECONDS
        if value is None:
            return
        import math
        if not math.isfinite(value) or value < 0:
            return
        key = _metric_key(name, labels)
        if not _can_create_series(histograms, key, name):
            return
        sample = histograms.get(key)
        if sample is None:
            sample = {
                "buckets": list(buckets),
                "counts": [0] * len(buckets),
                "count": 0,
                "help": help_text,
                "labels": dict(labels),
                "sum": 0,
            }
            histograms[key] = sample
        sample["count"] += 1
        sample["sum"] += value
        for i, bucket in enumerate(sample["buckets"]):
            if bucket is not None and value <= bucket:
                sample["counts"][i] = (sample["counts"][i] or 0) + 1

    def snapshot() -> dict[str, Any]:
        nonlocal dropped_series
        counter_snapshot = dict(counters)
        if dropped_series > 0:
            counter_snapshot[_metric_key(DROPPED_SERIES_COUNTER_NAME, {})] = {
                "help": "Prometheus metric series dropped because the exporter series cap was reached.",
                "labels": {},
                "value": dropped_series,
            }
        return {
            "counters": counter_snapshot,
            "gauges": dict(gauges),
            "histograms": dict(histograms),
        }

    def reset() -> None:
        nonlocal dropped_series
        counters.clear()
        gauges.clear()
        histograms.clear()
        dropped_series = 0

    return {"counter": counter, "gauge": gauge, "histogram": histogram, "reset": reset, "snapshot": snapshot}


def _safe_error_message(err: Any) -> str:
    if isinstance(err, Exception):
        message = err.message if hasattr(err, "message") else str(err)
    else:
        message = str(err)
    redacted = redact_sensitive_text(message)
    redacted = redacted.replace("\x00", " ")
    redacted = re.sub(r"[\r\n\t\u2028\u2029]", " ", redacted)
    return redacted[:500]


def _should_record_diagnostic_event(metadata: DiagnosticEventMetadata) -> bool:
    return metadata.get("trusted", False) or is_internal_diagnostic_event_metadata(metadata)


def render_prometheus_metrics(store: dict[str, Any]) -> str:
    snap = store["snapshot"]()
    lines: list[str] = []
    emitted: set[str] = set()

    def emit_header(name: str, type_str: str, help_text: str) -> None:
        if name in emitted:
            return
        emitted.add(name)
        lines.append(f"# HELP {name} {_escape_help(help_text)}")
        lines.append(f"# TYPE {name} {type_str}")

    for key, sample in sorted(snap["counters"].items(), key=lambda x: x[0]):
        name = key.split("|", 1)[0]
        emit_header(name, "counter", sample["help"])
        lines.append(f"{name}{_format_labels(sample['labels'])} {_format_prometheus_number(sample['value'])}")

    for key, sample in sorted(snap["gauges"].items(), key=lambda x: x[0]):
        name = key.split("|", 1)[0]
        emit_header(name, "gauge", sample["help"])
        lines.append(f"{name}{_format_labels(sample['labels'])} {_format_prometheus_number(sample['value'])}")

    for key, sample in sorted(snap["histograms"].items(), key=lambda x: x[0]):
        name = key.split("|", 1)[0]
        emit_header(name, "histogram", sample["help"])
        for i, bucket in enumerate(sample["buckets"]):
            if bucket is None:
                continue
            lines.append(
                f"{name}_bucket{_format_labels({**sample['labels'], 'le': str(bucket)})} "
                f"{_format_prometheus_number(sample['counts'][i] or 0)}"
            )
        lines.append(
            f"{name}_bucket{_format_labels({**sample['labels'], 'le': '+Inf'})} "
            f"{_format_prometheus_number(sample['count'])}"
        )
        lines.append(f"{name}_sum{_format_labels(sample['labels'])} {_format_prometheus_number(sample['sum'])}")
        lines.append(f"{name}_count{_format_labels(sample['labels'])} {_format_prometheus_number(sample['count'])}")

    lines.append("")
    return "\n".join(lines)


def _run_labels(evt: dict[str, Any]) -> dict[str, str]:
    result: dict[str, str] = {}
    if evt.get("blockedBy"):
        result["blocked_by"] = _low_cardinality_label(evt["blockedBy"])
    result["channel"] = _low_cardinality_label(evt.get("channel"))
    result["model"] = _low_cardinality_label(evt.get("model"))
    result["outcome"] = _low_cardinality_label(evt.get("outcome"), "unknown")
    result["provider"] = _low_cardinality_label(evt.get("provider"))
    result["trigger"] = _low_cardinality_label(evt.get("trigger"))
    return result


def _model_call_labels(evt: dict[str, Any]) -> dict[str, str]:
    result = {
        "api": _low_cardinality_label(evt.get("api")),
        "error_category": "none",
        "model": _low_cardinality_label(evt.get("model")),
        "outcome": "completed",
        "provider": _low_cardinality_label(evt.get("provider")),
        "transport": _low_cardinality_label(evt.get("transport")),
    }
    if evt.get("type") == "model.call.error":
        result["error_category"] = _low_cardinality_label(evt.get("errorCategory"), "other")
        result["outcome"] = "error"
    return result


def _model_failover_labels(evt: dict[str, Any]) -> dict[str, str]:
    return {
        "from_model": _low_cardinality_label(evt.get("fromModel")),
        "from_provider": _low_cardinality_label(evt.get("fromProvider")),
        "lane": _low_cardinality_queue_lane_label(evt.get("lane")),
        "reason": _low_cardinality_label(evt.get("reason"), "other"),
        "suspended": str(evt.get("suspended", "unknown")),
        "to_model": _low_cardinality_label(evt.get("toModel")),
        "to_provider": _low_cardinality_label(evt.get("toProvider")),
    }


def _tool_execution_labels(evt: dict[str, Any]) -> dict[str, str]:
    result = {
        "error_category": "none",
        "outcome": "completed",
        "params_kind": _low_cardinality_label(evt.get("paramsSummary", {}).get("kind") if isinstance(evt.get("paramsSummary"), dict) else None),
        "tool": _low_cardinality_label(evt.get("toolName"), "tool"),
        "tool_owner": _low_cardinality_label(evt.get("toolOwner"), "none"),
        "tool_source": _low_cardinality_label(evt.get("toolSource"), "core"),
    }
    if evt.get("type") == "tool.execution.error":
        result["error_category"] = _low_cardinality_label(evt.get("errorCategory"), "other")
        result["outcome"] = "error"
    return result


def _tool_execution_blocked_labels(evt: dict[str, Any]) -> dict[str, str]:
    return {
        "denied_reason": _low_cardinality_label(evt.get("deniedReason"), "other"),
        "params_kind": _low_cardinality_label(evt.get("paramsSummary", {}).get("kind") if isinstance(evt.get("paramsSummary"), dict) else None),
        "tool": _low_cardinality_label(evt.get("toolName"), "tool"),
        "tool_owner": _low_cardinality_label(evt.get("toolOwner"), "none"),
        "tool_source": _low_cardinality_label(evt.get("toolSource"), "core"),
    }


def _skill_labels(evt: dict[str, Any]) -> dict[str, str]:
    return {
        "activation": _low_cardinality_label(evt.get("activation"), "unknown"),
        "agent": _low_cardinality_label(evt.get("agentId")),
        "skill": _low_cardinality_label(evt.get("skillName"), "skill"),
        "source": _low_cardinality_label(evt.get("skillSource")),
    }


def _harness_labels(evt: dict[str, Any]) -> dict[str, str]:
    result = {
        "channel": _low_cardinality_label(evt.get("channel")),
        "error_category": "none",
        "harness": _low_cardinality_label(evt.get("harnessId")),
        "model": _low_cardinality_label(evt.get("model")),
        "outcome": _low_cardinality_label(evt.get("outcome")),
        "phase": "none",
        "plugin": _low_cardinality_label(evt.get("pluginId")),
        "provider": _low_cardinality_label(evt.get("provider")),
    }
    if evt.get("type") == "harness.run.error":
        result["error_category"] = _low_cardinality_label(evt.get("errorCategory"), "other")
        result["outcome"] = "error"
        result["phase"] = _low_cardinality_label(evt.get("phase"))
    return result


def _webhook_labels(evt: dict[str, Any]) -> dict[str, str]:
    return {
        "channel": _low_cardinality_label(evt.get("channel")),
        "webhook": _low_cardinality_label(evt.get("updateType")),
    }


def _session_stuck_labels(evt: dict[str, Any]) -> dict[str, str]:
    return {
        "reason": _low_cardinality_label(evt.get("reason"), "none"),
        "state": evt.get("state", "unknown"),
    }


def _session_recovery_labels(evt: dict[str, Any]) -> dict[str, str]:
    if evt.get("type") == "session.recovery.completed":
        action = _low_cardinality_label(evt.get("action"), "unknown")
        status = evt.get("status", "completed")
    else:
        action = "abort" if evt.get("allowActiveAbort") else "recover"
        status = "requested"
    return {
        "action": action,
        "active_work_kind": _low_cardinality_label(evt.get("activeWorkKind"), "none"),
        "state": evt.get("state", "unknown"),
        "status": status,
    }


def _liveness_labels(evt: dict[str, Any]) -> dict[str, str]:
    return {
        "reason": _low_cardinality_label(":".join(evt.get("reasons", [])), "unknown"),
    }


def _payload_large_labels(evt: dict[str, Any]) -> dict[str, str]:
    return {
        "action": evt.get("action", "unknown"),
        "channel": _low_cardinality_label(evt.get("channel"), "none"),
        "plugin": _low_cardinality_label(evt.get("pluginId"), "none"),
        "reason": _low_cardinality_label(evt.get("reason"), "none"),
        "surface": _low_cardinality_label(evt.get("surface"), "unknown"),
    }


def _talk_labels(evt: dict[str, Any]) -> dict[str, str]:
    return {
        "brain": _low_cardinality_label(evt.get("brain")),
        "event_type": _low_cardinality_label(evt.get("talkEventType")),
        "mode": _low_cardinality_label(evt.get("mode")),
        "provider": _low_cardinality_label(evt.get("provider")),
        "transport": _low_cardinality_label(evt.get("transport")),
    }


def _record_model_usage(store: dict[str, Any], evt: dict[str, Any]) -> None:
    labels = {
        "agent": _low_cardinality_label(evt.get("agentId")),
        "channel": _low_cardinality_label(evt.get("channel")),
        "model": _low_cardinality_label(evt.get("model")),
        "provider": _low_cardinality_label(evt.get("provider")),
    }
    usage = evt.get("usage", {})

    def _record_tokens(token_type: str, value: int | float | None) -> None:
        amount = _numeric_value(value)
        if amount is None or amount == 0:
            return
        store["counter"](
            "openclaw_model_tokens_total",
            "Model tokens reported by diagnostic usage events.",
            {**labels, "token_type": token_type},
            amount,
        )
        if token_type in ("input", "output"):
            store["histogram"](
                "openclaw_gen_ai_client_token_usage",
                "GenAI token usage distribution for input and output tokens.",
                {
                    "model": labels["model"],
                    "provider": labels["provider"],
                    "token_type": token_type,
                },
                amount,
                TOKEN_BUCKETS,
            )

    _record_tokens("input", usage.get("input"))
    _record_tokens("output", usage.get("output"))
    _record_tokens("cache_read", usage.get("cacheRead"))
    _record_tokens("cache_write", usage.get("cacheWrite"))
    _record_tokens("prompt", usage.get("promptTokens"))
    _record_tokens("total", usage.get("total"))

    store["counter"](
        "openclaw_model_cost_usd_total",
        "Estimated model cost in USD reported by diagnostic usage events.",
        labels,
        _numeric_value(evt.get("costUsd")) or 0,
    )
    store["histogram"](
        "openclaw_model_usage_duration_seconds",
        "Model usage event duration in seconds.",
        labels,
        _seconds(evt.get("durationMs")),
    )


def record_diagnostic_event(
    store: dict[str, Any],
    evt: DiagnosticEventPayload,
    metadata: DiagnosticEventMetadata,
) -> None:
    if not _should_record_diagnostic_event(metadata):
        return

    evt_type = evt.get("type", "")

    if evt_type == "model.usage":
        _record_model_usage(store, evt)
        return

    if evt_type == "run.completed":
        store["histogram"](
            "openclaw_run_duration_seconds",
            "Agent run duration in seconds.",
            _run_labels(evt),
            _seconds(evt.get("durationMs")),
        )
        store["counter"](
            "openclaw_run_completed_total",
            "Agent runs completed by outcome.",
            _run_labels(evt),
        )
        return

    if evt_type in ("model.call.completed", "model.call.error"):
        store["histogram"](
            "openclaw_model_call_duration_seconds",
            "Provider model call duration in seconds.",
            _model_call_labels(evt),
            _seconds(evt.get("durationMs")),
        )
        store["counter"](
            "openclaw_model_call_total",
            "Provider model calls completed by outcome.",
            _model_call_labels(evt),
        )
        return

    if evt_type == "model.failover":
        store["counter"](
            "openclaw_model_failover_total",
            "Model failovers by source, destination, lane, and reason.",
            _model_failover_labels(evt),
        )
        return

    if evt_type in ("tool.execution.completed", "tool.execution.error"):
        store["histogram"](
            "openclaw_tool_execution_duration_seconds",
            "Tool execution duration in seconds.",
            _tool_execution_labels(evt),
            _seconds(evt.get("durationMs")),
        )
        store["counter"](
            "openclaw_tool_execution_total",
            "Tool executions completed by outcome.",
            _tool_execution_labels(evt),
        )
        return

    if evt_type == "tool.execution.blocked":
        store["counter"](
            "openclaw_tool_execution_blocked_total",
            "Tool executions blocked by policy or sandbox diagnostics.",
            _tool_execution_blocked_labels(evt),
        )
        return

    if evt_type == "skill.used":
        store["counter"](
            "openclaw_skill_used_total",
            "Skills used by agent runs.",
            _skill_labels(evt),
        )
        return

    if evt_type in ("harness.run.completed", "harness.run.error"):
        store["histogram"](
            "openclaw_harness_run_duration_seconds",
            "Agent harness run duration in seconds.",
            _harness_labels(evt),
            _seconds(evt.get("durationMs")),
        )
        store["counter"](
            "openclaw_harness_run_total",
            "Agent harness runs completed by outcome.",
            _harness_labels(evt),
        )
        return

    if evt_type == "message.processed":
        channel = _low_cardinality_label(evt.get("channel"))
        outcome = evt.get("outcome", "unknown")
        reason = _low_cardinality_label(evt.get("reason"), "none")
        store["counter"](
            "openclaw_message_processed_total",
            "Inbound messages processed by outcome.",
            {"channel": channel, "outcome": outcome, "reason": reason},
        )
        store["histogram"](
            "openclaw_message_processed_duration_seconds",
            "Inbound message processing duration in seconds.",
            {"channel": channel, "outcome": outcome, "reason": reason},
            _seconds(evt.get("durationMs")),
        )
        return

    if evt_type == "webhook.received":
        store["counter"](
            "openclaw_webhook_received_total",
            "Webhook requests received by channel and update type.",
            _webhook_labels(evt),
        )
        return

    if evt_type == "webhook.processed":
        store["histogram"](
            "openclaw_webhook_duration_seconds",
            "Webhook processing duration in seconds.",
            _webhook_labels(evt),
            _seconds(evt.get("durationMs")),
        )
        return

    if evt_type == "webhook.error":
        store["counter"](
            "openclaw_webhook_error_total",
            "Webhook processing errors by channel and update type.",
            _webhook_labels(evt),
        )
        return

    if evt_type == "message.delivery.started":
        store["counter"](
            "openclaw_message_delivery_started_total",
            "Outbound message delivery attempts started.",
            {
                "channel": _low_cardinality_label(evt.get("channel")),
                "delivery_kind": _low_cardinality_label(evt.get("deliveryKind"), "other"),
            },
        )
        return

    if evt_type == "message.received":
        store["counter"](
            "openclaw_message_received_total",
            "Inbound messages received by channel.",
            {
                "channel": _low_cardinality_label(evt.get("channel")),
                "source": _low_cardinality_label(evt.get("source")),
            },
        )
        return

    if evt_type == "message.dispatch.started":
        store["counter"](
            "openclaw_message_dispatch_started_total",
            "Inbound message dispatch attempts started by channel.",
            {
                "channel": _low_cardinality_label(evt.get("channel")),
                "source": _low_cardinality_label(evt.get("source")),
            },
        )
        return

    if evt_type == "message.dispatch.completed":
        channel = _low_cardinality_label(evt.get("channel"))
        outcome = evt.get("outcome", "unknown")
        reason = _low_cardinality_label(evt.get("reason"), "none")
        source = _low_cardinality_label(evt.get("source"))
        store["counter"](
            "openclaw_message_dispatch_completed_total",
            "Inbound message dispatch attempts completed by outcome.",
            {"channel": channel, "outcome": outcome, "reason": reason, "source": source},
        )
        store["histogram"](
            "openclaw_message_dispatch_duration_seconds",
            "Inbound message dispatch duration in seconds.",
            {"channel": channel, "outcome": outcome, "reason": reason, "source": source},
            _seconds(evt.get("durationMs")),
        )
        return

    if evt_type in ("message.delivery.completed", "message.delivery.error"):
        channel = _low_cardinality_label(evt.get("channel"))
        delivery_kind = _low_cardinality_label(evt.get("deliveryKind"), "other")
        error_category = "none"
        outcome = "completed"
        if evt_type == "message.delivery.error":
            error_category = _low_cardinality_label(evt.get("errorCategory"), "other")
            outcome = "error"
        labels = {
            "channel": channel,
            "delivery_kind": delivery_kind,
            "error_category": error_category,
            "outcome": outcome,
        }
        store["counter"](
            "openclaw_message_delivery_total",
            "Outbound message delivery attempts by outcome.",
            labels,
        )
        store["histogram"](
            "openclaw_message_delivery_duration_seconds",
            "Outbound message delivery duration in seconds.",
            labels,
            _seconds(evt.get("durationMs")),
        )
        return

    if evt_type == "talk.event":
        labels = _talk_labels(evt)
        store["counter"](
            "openclaw_talk_event_total",
            "Talk events emitted by type.",
            labels,
        )
        store["histogram"](
            "openclaw_talk_event_duration_seconds",
            "Talk event duration in seconds when reported.",
            labels,
            _seconds(evt.get("durationMs")),
        )
        store["histogram"](
            "openclaw_talk_audio_bytes",
            "Talk audio frame byte lengths.",
            labels,
            _numeric_value(evt.get("byteLength")),
            BYTE_BUCKETS,
        )
        return

    if evt_type in ("session.recovery.requested", "session.recovery.completed"):
        labels = _session_recovery_labels(evt)
        store["counter"](
            "openclaw_session_recovery_total",
            "Session recovery observations by status and action.",
            labels,
        )
        store["histogram"](
            "openclaw_session_recovery_age_seconds",
            "Age of sessions selected for recovery in seconds.",
            labels,
            _seconds(evt.get("ageMs")),
        )
        return

    if evt_type in ("queue.lane.enqueue", "queue.lane.dequeue"):
        lane = _low_cardinality_queue_lane_label(evt.get("lane"))
        store["gauge"](
            "openclaw_queue_lane_size",
            "Current diagnostic queue lane size.",
            {"lane": lane},
            _numeric_value(evt.get("queueSize")),
        )
        if evt_type == "queue.lane.dequeue":
            store["histogram"](
                "openclaw_queue_lane_wait_seconds",
                "Queue lane wait time in seconds.",
                {"lane": lane},
                _seconds(evt.get("waitMs")),
            )
        return

    if evt_type == "session.state":
        store["counter"](
            "openclaw_session_state_total",
            "Session state observations.",
            {
                "reason": _low_cardinality_label(evt.get("reason"), "none"),
                "state": evt.get("state", "unknown"),
            },
        )
        if evt.get("queueDepth") is not None:
            store["gauge"](
                "openclaw_session_queue_depth",
                "Latest observed session queue depth.",
                {"state": evt.get("state", "unknown")},
                _numeric_value(evt.get("queueDepth")),
            )
        return

    if evt_type == "session.stuck":
        labels = _session_stuck_labels(evt)
        store["counter"](
            "openclaw_session_stuck_total",
            "Stale session bookkeeping observations with no active work.",
            labels,
        )
        store["histogram"](
            "openclaw_session_stuck_age_seconds",
            "Age of stale session bookkeeping observations in seconds.",
            labels,
            _seconds(evt.get("ageMs")),
        )
        return

    if evt_type == "session.turn.created":
        store["counter"](
            "openclaw_session_turn_created_total",
            "Agent session turns created.",
            {
                "agent": _low_cardinality_label(evt.get("agentId")),
                "channel": _low_cardinality_label(evt.get("channel")),
                "trigger": evt.get("trigger", "unknown"),
            },
        )
        return

    if evt_type == "diagnostic.memory.sample":
        store["gauge"](
            "openclaw_memory_bytes",
            "Latest process memory usage by memory kind.",
            {"kind": "rss"},
            _numeric_value(evt.get("memory", {}).get("rssBytes")),
        )
        store["gauge"](
            "openclaw_memory_bytes",
            "Latest process memory usage by memory kind.",
            {"kind": "heap_total"},
            _numeric_value(evt.get("memory", {}).get("heapTotalBytes")),
        )
        store["gauge"](
            "openclaw_memory_bytes",
            "Latest process memory usage by memory kind.",
            {"kind": "heap_used"},
            _numeric_value(evt.get("memory", {}).get("heapUsedBytes")),
        )
        store["histogram"](
            "openclaw_memory_rss_bytes",
            "RSS memory sample distribution in bytes.",
            {},
            _numeric_value(evt.get("memory", {}).get("rssBytes")),
            BYTE_BUCKETS,
        )
        return

    if evt_type == "diagnostic.memory.pressure":
        store["counter"](
            "openclaw_memory_pressure_total",
            "Memory pressure events by level and reason.",
            {
                "level": evt.get("level", "unknown"),
                "reason": evt.get("reason", "unknown"),
            },
        )
        return

    if evt_type == "diagnostic.liveness.warning":
        labels = _liveness_labels(evt)
        store["counter"](
            "openclaw_liveness_warning_total",
            "Diagnostic liveness warning events.",
            labels,
        )
        store["gauge"](
            "openclaw_liveness_sessions",
            "Latest session counts reported with diagnostic liveness warnings.",
            {"state": "active"},
            _numeric_value(evt.get("active")),
        )
        store["gauge"](
            "openclaw_liveness_sessions",
            "Latest session counts reported with diagnostic liveness warnings.",
            {"state": "waiting"},
            _numeric_value(evt.get("waiting")),
        )
        store["gauge"](
            "openclaw_liveness_sessions",
            "Latest session counts reported with diagnostic liveness warnings.",
            {"state": "queued"},
            _numeric_value(evt.get("queued")),
        )
        store["histogram"](
            "openclaw_liveness_event_loop_delay_p99_seconds",
            "P99 event-loop delay reported by diagnostic liveness warnings in seconds.",
            labels,
            _seconds(evt.get("eventLoopDelayP99Ms")),
        )
        store["histogram"](
            "openclaw_liveness_event_loop_delay_max_seconds",
            "Maximum event-loop delay reported by diagnostic liveness warnings in seconds.",
            labels,
            _seconds(evt.get("eventLoopDelayMaxMs")),
        )
        store["histogram"](
            "openclaw_liveness_event_loop_utilization_ratio",
            "Event-loop utilization reported by diagnostic liveness warnings.",
            labels,
            _numeric_value(evt.get("eventLoopUtilization")),
            RATIO_BUCKETS,
        )
        store["histogram"](
            "openclaw_liveness_cpu_core_ratio",
            "CPU core ratio reported by diagnostic liveness warnings.",
            labels,
            _numeric_value(evt.get("cpuCoreRatio")),
            RATIO_BUCKETS,
        )
        return

    if evt_type == "diagnostic.async_queue.dropped":
        store["counter"](
            "openclaw_diagnostic_async_queue_dropped_total",
            "Async diagnostic queue drops by dropped event class.",
            {"drop_class": "total"},
            _numeric_value(evt.get("droppedEvents")),
        )
        if evt.get("droppedTrustedEvents") is not None:
            store["counter"](
                "openclaw_diagnostic_async_queue_dropped_total",
                "Async diagnostic queue drops by dropped event class.",
                {"drop_class": "trusted"},
                _numeric_value(evt.get("droppedTrustedEvents")),
            )
        if evt.get("droppedUntrustedEvents") is not None:
            store["counter"](
                "openclaw_diagnostic_async_queue_dropped_total",
                "Async diagnostic queue drops by dropped event class.",
                {"drop_class": "untrusted"},
                _numeric_value(evt.get("droppedUntrustedEvents")),
            )
        if evt.get("droppedPriorityEvents") is not None:
            store["counter"](
                "openclaw_diagnostic_async_queue_dropped_total",
                "Async diagnostic queue drops by dropped event class.",
                {"drop_class": "priority"},
                _numeric_value(evt.get("droppedPriorityEvents")),
            )
        store["gauge"](
            "openclaw_diagnostic_async_queue_length",
            "Latest async diagnostic queue length after a drop summary.",
            {},
            _numeric_value(evt.get("queueLength")),
        )
        return

    if evt_type == "diagnostic.heartbeat":
        return

    if evt_type == "telemetry.exporter":
        store["counter"](
            "openclaw_telemetry_exporter_total",
            "Telemetry exporter lifecycle and failure events.",
            {
                "exporter": _low_cardinality_label(evt.get("exporter"), "unknown"),
                "reason": _low_cardinality_label(evt.get("reason"), "none"),
                "signal": evt.get("signal", "unknown"),
                "status": evt.get("status", "unknown"),
            },
        )
        return

    if evt_type == "payload.large":
        labels = _payload_large_labels(evt)
        store["counter"](
            "openclaw_payload_large_total",
            "Oversized payload diagnostics by surface and action.",
            labels,
        )
        store["histogram"](
            "openclaw_payload_large_bytes",
            "Oversized payload byte sizes by surface and action.",
            labels,
            _numeric_value(evt.get("bytes")),
            BYTE_BUCKETS,
        )


def _create_metrics_handler(store: dict[str, Any]) -> OpenClawPluginHttpRouteHandler:
    def handler(req: Any, res: Any) -> bool:
        method = req.method if hasattr(req, "method") else req.get("method", "")
        if method not in ("GET", "HEAD"):
            res.status_code = 405
            res.headers["Allow"] = "GET, HEAD"
            res.end("Method Not Allowed")
            return True

        body = render_prometheus_metrics(store)
        res.status_code = 200
        res.headers["Cache-Control"] = "no-store"
        res.headers["Content-Type"] = "text/plain; version=0.0.4; charset=utf-8"
        if method == "HEAD":
            res.end()
            return True
        res.end(body)
        return True

    return handler


def create_diagnostics_prometheus_exporter() -> dict[str, Any]:
    store = create_prometheus_metric_store()
    unsubscribe: Callable[[], None] | None = None

    service: OpenClawPluginService = {
        "id": "diagnostics-prometheus",
        "start": lambda ctx: _start_service(ctx, store, lambda u: setattr(service, "_unsubscribe", u)),
        "stop": lambda ctx: _stop_service(ctx, store),
    }

    def _start_service(ctx: OpenClawPluginServiceContext) -> None:
        subscribe = ctx.get("internal_diagnostics", {}).get("onEvent") if isinstance(ctx.get("internal_diagnostics"), dict) else None
        if subscribe is None:
            ctx.logger.error("diagnostics-prometheus: internal diagnostics capability unavailable")
            return

        def _on_event(evt: DiagnosticEventPayload, metadata: DiagnosticEventMetadata) -> None:
            try:
                record_diagnostic_event(store, evt, metadata)
            except Exception as err:
                ctx.logger.error(
                    f"diagnostics-prometheus: event handler failed ({evt.get('type', '?')}): {_safe_error_message(err)}"
                )

        unsubscribe_ref = subscribe(_on_event)
        unsubscribe = unsubscribe_ref

        internal_diag = ctx.get("internal_diagnostics")
        if isinstance(internal_diag, dict) and internal_diag.get("emit"):
            internal_diag.emit({
                "type": "telemetry.exporter",
                "exporter": "diagnostics-prometheus",
                "signal": "metrics",
                "status": "started",
                "reason": "configured",
            })

    def _stop_service(ctx: OpenClawPluginServiceContext) -> None:
        nonlocal unsubscribe
        if unsubscribe is not None:
            unsubscribe()
            unsubscribe = None
        store["reset"]()

    return {
        "handler": _create_metrics_handler(store),
        "render": lambda: render_prometheus_metrics(store),
        "service": service,
    }


test_api = {
    "create_prometheus_metric_store": create_prometheus_metric_store,
    "record_diagnostic_event": record_diagnostic_event,
    "render_prometheus_metrics": render_prometheus_metrics,
}

__test__ = test_api