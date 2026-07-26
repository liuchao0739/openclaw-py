"""Diagnostics Prometheus plugin module implements service behavior."""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass, field
from typing import Any, TypedDict

from openclaw_extensions.diagnostics_prometheus.api import (
    DiagnosticEventMetadata,
    DiagnosticEventPayload,
    OpenClawPluginHttpRouteHandler,
    OpenClawPluginServiceContext,
    is_internal_diagnostic_event_metadata,
    redact_sensitive_text,
)

LabelSet = dict[str, str]


class CounterSample(TypedDict):
    help: str
    labels: LabelSet
    value: float


class HistogramSample(TypedDict):
    buckets: list[float]
    counts: list[float]
    count: float
    help: str
    labels: LabelSet
    sum: float


class GaugeSample(TypedDict):
    help: str
    labels: LabelSet
    value: float


@dataclass
class MetricSnapshot:
    counters: dict[str, CounterSample]
    gauges: dict[str, GaugeSample]
    histograms: dict[str, HistogramSample]


@dataclass
class PrometheusMetricStore:
    counters: dict[str, CounterSample] = field(default_factory=dict)
    gauges: dict[str, GaugeSample] = field(default_factory=dict)
    histograms: dict[str, HistogramSample] = field(default_factory=dict)
    dropped_series: int = 0


DURATION_BUCKETS_SECONDS = [
    0.005,
    0.01,
    0.025,
    0.05,
    0.1,
    0.25,
    0.5,
    1,
    2.5,
    5,
    10,
    30,
    60,
    120,
    300,
    600,
]
TOKEN_BUCKETS = [1, 4, 16, 64, 256, 1024, 4096, 16384, 65536, 262144, 1048576]
BYTE_BUCKETS = [
    1024,
    4096,
    16384,
    65536,
    262144,
    1048576,
    4194304,
    16777216,
    67108864,
    268435456,
    1073741824,
    4294967296,
    17179869184,
]
RATIO_BUCKETS = [0.01, 0.05, 0.1, 0.25, 0.5, 0.75, 1, 2, 4, 8, 16]
LOW_CARDINALITY_VALUE_RE = re.compile(r"^[A-Za-z0-9_.:-]{1,120}$")
MAX_PROMETHEUS_SERIES = 2048
DROPPED_SERIES_COUNTER_NAME = "openclaw_prometheus_series_dropped_total"


def low_cardinality_label(value: str | None, fallback: str = "unknown") -> str:
    if not value:
        return fallback
    redacted = redact_sensitive_text(value.strip())
    redacted_lower = redacted.lower()
    if redacted_lower.startswith("agent:") or ":agent:" in redacted_lower:
        return fallback
    return redacted if LOW_CARDINALITY_VALUE_RE.fullmatch(redacted) else fallback


def low_cardinality_queue_lane_label(value: str | None, fallback: str = "unknown") -> str:
    if not value:
        return fallback
    redacted = redact_sensitive_text(value.strip())
    redacted_lower = redacted.lower()
    if redacted_lower.startswith("agent:"):
        return fallback
    scoped_lane_index = redacted.find(":")
    lane = redacted[:scoped_lane_index] if scoped_lane_index >= 0 else redacted
    return lane if LOW_CARDINALITY_VALUE_RE.fullmatch(lane) else fallback


def numeric_value(value: float | None) -> float | None:
    if not isinstance(value, (int, float)) or not (value >= 0 and math.isfinite(value)):
        return None
    return float(value)


def seconds(ms: float | None) -> float | None:
    value = numeric_value(ms)
    return None if value is None else value / 1000


def sorted_labels(labels: LabelSet) -> list[tuple[str, str]]:
    return sorted(labels.items(), key=lambda item: item[0])


def metric_key(name: str, labels: LabelSet) -> str:
    return f"{name}|{json.dumps(sorted_labels(labels))}"


def escape_help(value: str) -> str:
    return value.replace("\\", "\\\\").replace("\n", "\\n")


def escape_label_value(value: str) -> str:
    return value.replace("\\", "\\\\").replace("\n", "\\n").replace('"', '\\"')


def format_labels(labels: LabelSet) -> str:
    entries = sorted_labels(labels)
    if not entries:
        return ""
    return "{" + ",".join(f'{key}="{escape_label_value(value)}"' for key, value in entries) + "}"


def format_prometheus_number(value: float) -> str:
    if not math.isfinite(value):
        return "0"
    if float(value).is_integer():
        return str(int(value))
    return str(float(f"{value:.12g}"))


def create_prometheus_metric_store() -> PrometheusMetricStore:
    store = PrometheusMetricStore()

    def can_create_series(series_map: dict[str, Any], key: str, metric_name: str) -> bool:
        if key in series_map:
            return True
        if metric_name == DROPPED_SERIES_COUNTER_NAME:
            return True
        if len(store.counters) + len(store.gauges) + len(store.histograms) < MAX_PROMETHEUS_SERIES:
            return True
        store.dropped_series += 1
        return False

    def counter(name: str, help_text: str, labels: LabelSet, amount: float = 1) -> None:
        if not isinstance(amount, (int, float)) or amount <= 0:
            return
        key = metric_key(name, labels)
        if not can_create_series(store.counters, key, name):
            return
        existing = store.counters.get(key)
        if existing:
            existing["value"] += amount
            return
        store.counters[key] = {"help": help_text, "labels": labels, "value": amount}

    def gauge(name: str, help_text: str, labels: LabelSet, value: float | None) -> None:
        if value is None or not isinstance(value, (int, float)) or not math.isfinite(value):
            return
        key = metric_key(name, labels)
        if not can_create_series(store.gauges, key, name):
            return
        store.gauges[key] = {"help": help_text, "labels": labels, "value": float(value)}

    def histogram(
        name: str,
        help_text: str,
        labels: LabelSet,
        value: float | None,
        buckets: list[float] | None = None,
    ) -> None:
        if (
            value is None
            or not isinstance(value, (int, float))
            or value < 0
            or not math.isfinite(value)
        ):
            return
        bucket_list = buckets if buckets is not None else DURATION_BUCKETS_SECONDS
        key = metric_key(name, labels)
        if not can_create_series(store.histograms, key, name):
            return
        sample = store.histograms.get(key)
        if sample is None:
            sample = {
                "buckets": bucket_list,
                "counts": [0.0] * len(bucket_list),
                "count": 0.0,
                "help": help_text,
                "labels": labels,
                "sum": 0.0,
            }
            store.histograms[key] = sample
        sample["count"] += 1
        sample["sum"] += float(value)
        for index, bucket in enumerate(sample["buckets"]):
            if value <= bucket:
                sample["counts"][index] = (sample["counts"][index] or 0) + 1

    def snapshot() -> MetricSnapshot:
        counter_snapshot = dict(store.counters)
        if store.dropped_series > 0:
            counter_snapshot[metric_key(DROPPED_SERIES_COUNTER_NAME, {})] = {
                "help": "Prometheus metric series dropped because the exporter series cap was reached.",
                "labels": {},
                "value": float(store.dropped_series),
            }
        return MetricSnapshot(
            counters=counter_snapshot,
            gauges=dict(store.gauges),
            histograms=dict(store.histograms),
        )

    def reset() -> None:
        store.counters.clear()
        store.gauges.clear()
        store.histograms.clear()
        store.dropped_series = 0

    store.counter = counter  # type: ignore[attr-defined]
    store.gauge = gauge  # type: ignore[attr-defined]
    store.histogram = histogram  # type: ignore[attr-defined]
    store.snapshot = snapshot  # type: ignore[attr-defined]
    store.reset = reset  # type: ignore[attr-defined]
    return store


def safe_error_message(err: BaseException | Any) -> str:
    if isinstance(err, BaseException):
        message = err.args[0] if err.args else err.__class__.__name__
        message = str(message) if message is not None else err.__class__.__name__
    else:
        message = str(err)
    return (
        redact_sensitive_text(message)
        .replace("\x00", " ")
        .translate(str.maketrans({"\r": " ", "\n": " ", "\t": " ", "\u2028": " ", "\u2029": " "}))
        [:500]
    )


def should_record_diagnostic_event(metadata: DiagnosticEventMetadata) -> bool:
    return metadata.get("trusted") is True or is_internal_diagnostic_event_metadata(metadata)


def render_prometheus_metrics(store: PrometheusMetricStore) -> str:
    snapshot = store.snapshot()
    lines: list[str] = []
    emitted: set[str] = set()

    def emit_header(name: str, metric_type: str, help_text: str) -> None:
        if name in emitted:
            return
        emitted.add(name)
        lines.append(f"# HELP {name} {escape_help(help_text)}")
        lines.append(f"# TYPE {name} {metric_type}")

    for key, sample in sorted(snapshot.counters.items(), key=lambda item: item[0]):
        name = key.split("|", 1)[0]
        emit_header(name, "counter", sample["help"])
        lines.append(f"{name}{format_labels(sample['labels'])} {format_prometheus_number(sample['value'])}")

    for key, sample in sorted(snapshot.gauges.items(), key=lambda item: item[0]):
        name = key.split("|", 1)[0]
        emit_header(name, "gauge", sample["help"])
        lines.append(f"{name}{format_labels(sample['labels'])} {format_prometheus_number(sample['value'])}")

    for key, sample in sorted(snapshot.histograms.items(), key=lambda item: item[0]):
        name = key.split("|", 1)[0]
        emit_header(name, "histogram", sample["help"])
        for index, bucket in enumerate(sample["buckets"]):
            lines.append(
                f"{name}_bucket{format_labels({**sample['labels'], 'le': str(bucket)})} "
                f"{format_prometheus_number(sample['counts'][index] or 0)}"
            )
        lines.append(
            f"{name}_bucket{format_labels({**sample['labels'], 'le': '+Inf'})} "
            f"{format_prometheus_number(sample['count'])}"
        )
        lines.append(
            f"{name}_sum{format_labels(sample['labels'])} {format_prometheus_number(sample['sum'])}"
        )
        lines.append(
            f"{name}_count{format_labels(sample['labels'])} {format_prometheus_number(sample['count'])}"
        )

    lines.append("")
    return "\n".join(lines)


def run_labels(evt: dict[str, Any]) -> LabelSet:
    labels: LabelSet = {
        "channel": low_cardinality_label(evt.get("channel")),
        "model": low_cardinality_label(evt.get("model")),
        "outcome": low_cardinality_label(evt.get("outcome"), "unknown"),
        "provider": low_cardinality_label(evt.get("provider")),
        "trigger": low_cardinality_label(evt.get("trigger")),
    }
    if evt.get("blockedBy"):
        labels["blocked_by"] = low_cardinality_label(evt.get("blockedBy"))
    return labels


def model_call_labels(evt: dict[str, Any]) -> LabelSet:
    return {
        "api": low_cardinality_label(evt.get("api")),
        "error_category": (
            low_cardinality_label(evt.get("errorCategory"), "other")
            if evt.get("type") == "model.call.error"
            else "none"
        ),
        "model": low_cardinality_label(evt.get("model")),
        "outcome": "error" if evt.get("type") == "model.call.error" else "completed",
        "provider": low_cardinality_label(evt.get("provider")),
        "transport": low_cardinality_label(evt.get("transport")),
    }


def model_failover_labels(evt: dict[str, Any]) -> LabelSet:
    suspended = evt.get("suspended")
    return {
        "from_model": low_cardinality_label(evt.get("fromModel")),
        "from_provider": low_cardinality_label(evt.get("fromProvider")),
        "lane": low_cardinality_queue_lane_label(evt.get("lane")),
        "reason": low_cardinality_label(evt.get("reason"), "other"),
        "suspended": "unknown" if suspended is None else str(suspended).lower(),
        "to_model": low_cardinality_label(evt.get("toModel")),
        "to_provider": low_cardinality_label(evt.get("toProvider")),
    }


def tool_execution_labels(evt: dict[str, Any]) -> LabelSet:
    params_summary = evt.get("paramsSummary") or {}
    return {
        "error_category": (
            low_cardinality_label(evt.get("errorCategory"), "other")
            if evt.get("type") == "tool.execution.error"
            else "none"
        ),
        "outcome": "error" if evt.get("type") == "tool.execution.error" else "completed",
        "params_kind": low_cardinality_label(params_summary.get("kind")),
        "tool": low_cardinality_label(evt.get("toolName"), "tool"),
        "tool_owner": low_cardinality_label(evt.get("toolOwner"), "none"),
        "tool_source": low_cardinality_label(evt.get("toolSource"), "core"),
    }


def tool_execution_blocked_labels(evt: dict[str, Any]) -> LabelSet:
    params_summary = evt.get("paramsSummary") or {}
    return {
        "denied_reason": low_cardinality_label(evt.get("deniedReason"), "other"),
        "params_kind": low_cardinality_label(params_summary.get("kind")),
        "tool": low_cardinality_label(evt.get("toolName"), "tool"),
        "tool_owner": low_cardinality_label(evt.get("toolOwner"), "none"),
        "tool_source": low_cardinality_label(evt.get("toolSource"), "core"),
    }


def skill_labels(evt: dict[str, Any]) -> LabelSet:
    return {
        "activation": low_cardinality_label(evt.get("activation"), "unknown"),
        "agent": low_cardinality_label(evt.get("agentId")),
        "skill": low_cardinality_label(evt.get("skillName"), "skill"),
        "source": low_cardinality_label(evt.get("skillSource")),
    }


def harness_labels(evt: dict[str, Any]) -> LabelSet:
    return {
        "channel": low_cardinality_label(evt.get("channel")),
        "error_category": (
            low_cardinality_label(evt.get("errorCategory"), "other")
            if evt.get("type") == "harness.run.error"
            else "none"
        ),
        "harness": low_cardinality_label(evt.get("harnessId")),
        "model": low_cardinality_label(evt.get("model")),
        "outcome": (
            "error"
            if evt.get("type") == "harness.run.error"
            else low_cardinality_label(evt.get("outcome"))
        ),
        "phase": (
            low_cardinality_label(evt.get("phase"))
            if evt.get("type") == "harness.run.error"
            else "none"
        ),
        "plugin": low_cardinality_label(evt.get("pluginId")),
        "provider": low_cardinality_label(evt.get("provider")),
    }


def webhook_labels(evt: dict[str, Any]) -> LabelSet:
    return {
        "channel": low_cardinality_label(evt.get("channel")),
        "webhook": low_cardinality_label(evt.get("updateType")),
    }


def session_stuck_labels(evt: dict[str, Any]) -> LabelSet:
    return {
        "reason": low_cardinality_label(evt.get("reason"), "none"),
        "state": str(evt.get("state", "")),
    }


def session_recovery_labels(evt: dict[str, Any]) -> LabelSet:
    if evt.get("type") == "session.recovery.completed":
        action = low_cardinality_label(evt.get("action"), "unknown")
    else:
        action = "abort" if evt.get("allowActiveAbort") else "recover"
    return {
        "action": action,
        "active_work_kind": low_cardinality_label(evt.get("activeWorkKind"), "none"),
        "state": str(evt.get("state", "")),
        "status": evt.get("status") if evt.get("type") == "session.recovery.completed" else "requested",
    }


def liveness_labels(evt: dict[str, Any]) -> LabelSet:
    reasons = evt.get("reasons") or []
    return {
        "reason": low_cardinality_label(":".join(str(reason) for reason in reasons), "unknown"),
    }


def payload_large_labels(evt: dict[str, Any]) -> LabelSet:
    return {
        "action": str(evt.get("action", "")),
        "channel": low_cardinality_label(evt.get("channel"), "none"),
        "plugin": low_cardinality_label(evt.get("pluginId"), "none"),
        "reason": low_cardinality_label(evt.get("reason"), "none"),
        "surface": low_cardinality_label(evt.get("surface"), "unknown"),
    }


def talk_labels(evt: dict[str, Any]) -> LabelSet:
    return {
        "brain": low_cardinality_label(evt.get("brain")),
        "event_type": low_cardinality_label(evt.get("talkEventType")),
        "mode": low_cardinality_label(evt.get("mode")),
        "provider": low_cardinality_label(evt.get("provider")),
        "transport": low_cardinality_label(evt.get("transport")),
    }


def record_model_usage(store: PrometheusMetricStore, evt: dict[str, Any]) -> None:
    labels = {
        "agent": low_cardinality_label(evt.get("agentId")),
        "channel": low_cardinality_label(evt.get("channel")),
        "model": low_cardinality_label(evt.get("model")),
        "provider": low_cardinality_label(evt.get("provider")),
    }
    usage = evt.get("usage") or {}

    def record_tokens(token_type: str, value: float | None) -> None:
        amount = numeric_value(value)
        if amount is None or amount == 0:
            return
        store.counter(
            "openclaw_model_tokens_total",
            "Model tokens reported by diagnostic usage events.",
            {**labels, "token_type": token_type},
            amount,
        )
        if token_type in ("input", "output"):
            store.histogram(
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

    record_tokens("input", usage.get("input"))
    record_tokens("output", usage.get("output"))
    record_tokens("cache_read", usage.get("cacheRead"))
    record_tokens("cache_write", usage.get("cacheWrite"))
    record_tokens("prompt", usage.get("promptTokens"))
    record_tokens("total", usage.get("total"))

    store.counter(
        "openclaw_model_cost_usd_total",
        "Estimated model cost in USD reported by diagnostic usage events.",
        labels,
        numeric_value(evt.get("costUsd")) or 0,
    )
    store.histogram(
        "openclaw_model_usage_duration_seconds",
        "Model usage event duration in seconds.",
        labels,
        seconds(evt.get("durationMs")),
    )


def record_diagnostic_event(
    store: PrometheusMetricStore,
    evt: DiagnosticEventPayload,
    metadata: DiagnosticEventMetadata,
) -> None:
    if not should_record_diagnostic_event(metadata):
        return

    event_type = evt.get("type")
    if event_type == "model.usage":
        record_model_usage(store, evt)
        return
    if event_type == "run.completed":
        store.histogram(
            "openclaw_run_duration_seconds",
            "Agent run duration in seconds.",
            run_labels(evt),
            seconds(evt.get("durationMs")),
        )
        store.counter(
            "openclaw_run_completed_total",
            "Agent runs completed by outcome.",
            run_labels(evt),
        )
        return
    if event_type in ("model.call.completed", "model.call.error"):
        store.histogram(
            "openclaw_model_call_duration_seconds",
            "Provider model call duration in seconds.",
            model_call_labels(evt),
            seconds(evt.get("durationMs")),
        )
        store.counter(
            "openclaw_model_call_total",
            "Provider model calls completed by outcome.",
            model_call_labels(evt),
        )
        return
    if event_type == "model.failover":
        store.counter(
            "openclaw_model_failover_total",
            "Model failovers by source, destination, lane, and reason.",
            model_failover_labels(evt),
        )
        return
    if event_type in ("tool.execution.completed", "tool.execution.error"):
        store.histogram(
            "openclaw_tool_execution_duration_seconds",
            "Tool execution duration in seconds.",
            tool_execution_labels(evt),
            seconds(evt.get("durationMs")),
        )
        store.counter(
            "openclaw_tool_execution_total",
            "Tool executions completed by outcome.",
            tool_execution_labels(evt),
        )
        return
    if event_type == "tool.execution.blocked":
        store.counter(
            "openclaw_tool_execution_blocked_total",
            "Tool executions blocked by policy or sandbox diagnostics.",
            tool_execution_blocked_labels(evt),
        )
        return
    if event_type == "skill.used":
        store.counter(
            "openclaw_skill_used_total",
            "Skills used by agent runs.",
            skill_labels(evt),
        )
        return
    if event_type in ("harness.run.completed", "harness.run.error"):
        store.histogram(
            "openclaw_harness_run_duration_seconds",
            "Agent harness run duration in seconds.",
            harness_labels(evt),
            seconds(evt.get("durationMs")),
        )
        store.counter(
            "openclaw_harness_run_total",
            "Agent harness runs completed by outcome.",
            harness_labels(evt),
        )
        return
    if event_type == "message.processed":
        labels = {
            "channel": low_cardinality_label(evt.get("channel")),
            "outcome": str(evt.get("outcome", "")),
            "reason": low_cardinality_label(evt.get("reason"), "none"),
        }
        store.counter(
            "openclaw_message_processed_total",
            "Inbound messages processed by outcome.",
            labels,
        )
        store.histogram(
            "openclaw_message_processed_duration_seconds",
            "Inbound message processing duration in seconds.",
            labels,
            seconds(evt.get("durationMs")),
        )
        return
    if event_type == "webhook.received":
        store.counter(
            "openclaw_webhook_received_total",
            "Webhook requests received by channel and update type.",
            webhook_labels(evt),
        )
        return
    if event_type == "webhook.processed":
        store.histogram(
            "openclaw_webhook_duration_seconds",
            "Webhook processing duration in seconds.",
            webhook_labels(evt),
            seconds(evt.get("durationMs")),
        )
        return
    if event_type == "webhook.error":
        store.counter(
            "openclaw_webhook_error_total",
            "Webhook processing errors by channel and update type.",
            webhook_labels(evt),
        )
        return
    if event_type == "message.delivery.started":
        store.counter(
            "openclaw_message_delivery_started_total",
            "Outbound message delivery attempts started.",
            {
                "channel": low_cardinality_label(evt.get("channel")),
                "delivery_kind": low_cardinality_label(evt.get("deliveryKind"), "other"),
            },
        )
        return
    if event_type == "message.received":
        store.counter(
            "openclaw_message_received_total",
            "Inbound messages received by channel.",
            {
                "channel": low_cardinality_label(evt.get("channel")),
                "source": low_cardinality_label(evt.get("source")),
            },
        )
        return
    if event_type == "message.dispatch.started":
        store.counter(
            "openclaw_message_dispatch_started_total",
            "Inbound message dispatch attempts started by channel.",
            {
                "channel": low_cardinality_label(evt.get("channel")),
                "source": low_cardinality_label(evt.get("source")),
            },
        )
        return
    if event_type == "message.dispatch.completed":
        labels = {
            "channel": low_cardinality_label(evt.get("channel")),
            "outcome": str(evt.get("outcome", "")),
            "reason": low_cardinality_label(evt.get("reason"), "none"),
            "source": low_cardinality_label(evt.get("source")),
        }
        store.counter(
            "openclaw_message_dispatch_completed_total",
            "Inbound message dispatch attempts completed by outcome.",
            labels,
        )
        store.histogram(
            "openclaw_message_dispatch_duration_seconds",
            "Inbound message dispatch duration in seconds.",
            labels,
            seconds(evt.get("durationMs")),
        )
        return
    if event_type in ("message.delivery.completed", "message.delivery.error"):
        labels = {
            "channel": low_cardinality_label(evt.get("channel")),
            "delivery_kind": low_cardinality_label(evt.get("deliveryKind"), "other"),
            "error_category": (
                low_cardinality_label(evt.get("errorCategory"), "other")
                if event_type == "message.delivery.error"
                else "none"
            ),
            "outcome": "error" if event_type == "message.delivery.error" else "completed",
        }
        store.counter(
            "openclaw_message_delivery_total",
            "Outbound message delivery attempts by outcome.",
            labels,
        )
        store.histogram(
            "openclaw_message_delivery_duration_seconds",
            "Outbound message delivery duration in seconds.",
            labels,
            seconds(evt.get("durationMs")),
        )
        return
    if event_type == "talk.event":
        labels = talk_labels(evt)
        store.counter(
            "openclaw_talk_event_total",
            "Talk events emitted by type.",
            labels,
        )
        store.histogram(
            "openclaw_talk_event_duration_seconds",
            "Talk event duration in seconds when reported.",
            labels,
            seconds(evt.get("durationMs")),
        )
        store.histogram(
            "openclaw_talk_audio_bytes",
            "Talk audio frame byte lengths.",
            labels,
            numeric_value(evt.get("byteLength")),
            BYTE_BUCKETS,
        )
        return
    if event_type in ("session.recovery.requested", "session.recovery.completed"):
        labels = session_recovery_labels(evt)
        store.counter(
            "openclaw_session_recovery_total",
            "Session recovery observations by status and action.",
            labels,
        )
        store.histogram(
            "openclaw_session_recovery_age_seconds",
            "Age of sessions selected for recovery in seconds.",
            labels,
            seconds(evt.get("ageMs")),
        )
        return
    if event_type in ("queue.lane.enqueue", "queue.lane.dequeue"):
        lane_labels = {"lane": low_cardinality_queue_lane_label(evt.get("lane"))}
        store.gauge(
            "openclaw_queue_lane_size",
            "Current diagnostic queue lane size.",
            lane_labels,
            numeric_value(evt.get("queueSize")),
        )
        if event_type == "queue.lane.dequeue":
            store.histogram(
                "openclaw_queue_lane_wait_seconds",
                "Queue lane wait time in seconds.",
                lane_labels,
                seconds(evt.get("waitMs")),
            )
        return
    if event_type == "session.state":
        store.counter(
            "openclaw_session_state_total",
            "Session state observations.",
            {
                "reason": low_cardinality_label(evt.get("reason"), "none"),
                "state": str(evt.get("state", "")),
            },
        )
        if evt.get("queueDepth") is not None:
            store.gauge(
                "openclaw_session_queue_depth",
                "Latest observed session queue depth.",
                {"state": str(evt.get("state", ""))},
                numeric_value(evt.get("queueDepth")),
            )
        return
    if event_type == "session.stuck":
        labels = session_stuck_labels(evt)
        store.counter(
            "openclaw_session_stuck_total",
            "Stale session bookkeeping observations with no active work.",
            labels,
        )
        store.histogram(
            "openclaw_session_stuck_age_seconds",
            "Age of stale session bookkeeping observations in seconds.",
            labels,
            seconds(evt.get("ageMs")),
        )
        return
    if event_type == "session.turn.created":
        store.counter(
            "openclaw_session_turn_created_total",
            "Agent session turns created.",
            {
                "agent": low_cardinality_label(evt.get("agentId")),
                "channel": low_cardinality_label(evt.get("channel")),
                "trigger": str(evt.get("trigger", "")),
            },
        )
        return
    if event_type == "diagnostic.memory.sample":
        memory = evt.get("memory") or {}
        store.gauge(
            "openclaw_memory_bytes",
            "Latest process memory usage by memory kind.",
            {"kind": "rss"},
            memory.get("rssBytes"),
        )
        store.gauge(
            "openclaw_memory_bytes",
            "Latest process memory usage by memory kind.",
            {"kind": "heap_total"},
            memory.get("heapTotalBytes"),
        )
        store.gauge(
            "openclaw_memory_bytes",
            "Latest process memory usage by memory kind.",
            {"kind": "heap_used"},
            memory.get("heapUsedBytes"),
        )
        store.histogram(
            "openclaw_memory_rss_bytes",
            "RSS memory sample distribution in bytes.",
            {},
            numeric_value(memory.get("rssBytes")),
            BYTE_BUCKETS,
        )
        return
    if event_type == "diagnostic.memory.pressure":
        store.counter(
            "openclaw_memory_pressure_total",
            "Memory pressure events by level and reason.",
            {
                "level": str(evt.get("level", "")),
                "reason": str(evt.get("reason", "")),
            },
        )
        return
    if event_type == "diagnostic.liveness.warning":
        labels = liveness_labels(evt)
        store.counter(
            "openclaw_liveness_warning_total",
            "Diagnostic liveness warning events.",
            labels,
        )
        store.gauge(
            "openclaw_liveness_sessions",
            "Latest session counts reported with diagnostic liveness warnings.",
            {"state": "active"},
            numeric_value(evt.get("active")),
        )
        store.gauge(
            "openclaw_liveness_sessions",
            "Latest session counts reported with diagnostic liveness warnings.",
            {"state": "waiting"},
            numeric_value(evt.get("waiting")),
        )
        store.gauge(
            "openclaw_liveness_sessions",
            "Latest session counts reported with diagnostic liveness warnings.",
            {"state": "queued"},
            numeric_value(evt.get("queued")),
        )
        store.histogram(
            "openclaw_liveness_event_loop_delay_p99_seconds",
            "P99 event-loop delay reported by diagnostic liveness warnings in seconds.",
            labels,
            seconds(evt.get("eventLoopDelayP99Ms")),
        )
        store.histogram(
            "openclaw_liveness_event_loop_delay_max_seconds",
            "Maximum event-loop delay reported by diagnostic liveness warnings in seconds.",
            labels,
            seconds(evt.get("eventLoopDelayMaxMs")),
        )
        store.histogram(
            "openclaw_liveness_event_loop_utilization_ratio",
            "Event-loop utilization reported by diagnostic liveness warnings.",
            labels,
            numeric_value(evt.get("eventLoopUtilization")),
            RATIO_BUCKETS,
        )
        store.histogram(
            "openclaw_liveness_cpu_core_ratio",
            "CPU core ratio reported by diagnostic liveness warnings.",
            labels,
            numeric_value(evt.get("cpuCoreRatio")),
            RATIO_BUCKETS,
        )
        return
    if event_type == "diagnostic.async_queue.dropped":
        store.counter(
            "openclaw_diagnostic_async_queue_dropped_total",
            "Async diagnostic queue drops by dropped event class.",
            {"drop_class": "total"},
            numeric_value(evt.get("droppedEvents")),
        )
        if evt.get("droppedTrustedEvents") is not None:
            store.counter(
                "openclaw_diagnostic_async_queue_dropped_total",
                "Async diagnostic queue drops by dropped event class.",
                {"drop_class": "trusted"},
                numeric_value(evt.get("droppedTrustedEvents")),
            )
        if evt.get("droppedUntrustedEvents") is not None:
            store.counter(
                "openclaw_diagnostic_async_queue_dropped_total",
                "Async diagnostic queue drops by dropped event class.",
                {"drop_class": "untrusted"},
                numeric_value(evt.get("droppedUntrustedEvents")),
            )
        if evt.get("droppedPriorityEvents") is not None:
            store.counter(
                "openclaw_diagnostic_async_queue_dropped_total",
                "Async diagnostic queue drops by dropped event class.",
                {"drop_class": "priority"},
                numeric_value(evt.get("droppedPriorityEvents")),
            )
        store.gauge(
            "openclaw_diagnostic_async_queue_length",
            "Latest async diagnostic queue length after a drop summary.",
            {},
            numeric_value(evt.get("queueLength")),
        )
        return
    if event_type == "diagnostic.heartbeat":
        return
    if event_type == "telemetry.exporter":
        store.counter(
            "openclaw_telemetry_exporter_total",
            "Telemetry exporter lifecycle events.",
            {
                "exporter": low_cardinality_label(evt.get("exporter")),
                "reason": low_cardinality_label(evt.get("reason"), "none"),
                "signal": str(evt.get("signal", "")),
                "status": str(evt.get("status", "")),
            },
        )
        return
    if event_type == "payload.large":
        labels = payload_large_labels(evt)
        store.counter(
            "openclaw_payload_large_total",
            "Oversized payload diagnostics by surface and action.",
            labels,
        )
        store.histogram(
            "openclaw_payload_large_bytes",
            "Oversized payload byte sizes by surface and action.",
            labels,
            numeric_value(evt.get("bytes")),
            BYTE_BUCKETS,
        )


def create_metrics_handler(store: PrometheusMetricStore) -> OpenClawPluginHttpRouteHandler:
    def handler(req: Any, res: Any) -> bool:
        method = getattr(req, "method", "GET") or "GET"
        if method not in ("GET", "HEAD"):
            res.statusCode = 405
            res.setHeader("Allow", "GET, HEAD")
            res.end("Method Not Allowed")
            return True

        body = render_prometheus_metrics(store)
        res.statusCode = 200
        res.setHeader("Cache-Control", "no-store")
        res.setHeader("Content-Type", "text/plain; version=0.0.4; charset=utf-8")
        if method == "HEAD":
            res.end()
            return True
        res.end(body)
        return True

    return handler


class DiagnosticsPrometheusService:
    id = "diagnostics-prometheus"

    def __init__(self, store: PrometheusMetricStore) -> None:
        self._store = store
        self._unsubscribe: Any | None = None

    def start(self, ctx: OpenClawPluginServiceContext) -> None:
        internal_diagnostics = getattr(ctx, "internal_diagnostics", None)
        subscribe = getattr(internal_diagnostics, "on_event", None) if internal_diagnostics else None
        if not subscribe:
            ctx.logger.error("diagnostics-prometheus: internal diagnostics capability unavailable")
            return

        def on_event(
            event: DiagnosticEventPayload,
            metadata: DiagnosticEventMetadata,
            _private_data: Any = None,
        ) -> None:
            try:
                record_diagnostic_event(self._store, event, metadata)
            except Exception as err:  # noqa: BLE001
                ctx.logger.error(
                    "diagnostics-prometheus: event handler failed "
                    f"({event.get('type')}): {safe_error_message(err)}"
                )

        self._unsubscribe = subscribe(on_event)
        emit = getattr(internal_diagnostics, "emit", None)
        if emit:
            emit(
                {
                    "type": "telemetry.exporter",
                    "exporter": "diagnostics-prometheus",
                    "signal": "metrics",
                    "status": "started",
                    "reason": "configured",
                }
            )

    def stop(self, ctx: OpenClawPluginServiceContext | None = None) -> None:
        del ctx
        if self._unsubscribe:
            self._unsubscribe()
        self._unsubscribe = None
        self._store.reset()


def create_diagnostics_prometheus_exporter() -> dict[str, Any]:
    store = create_prometheus_metric_store()
    service = DiagnosticsPrometheusService(store)
    return {
        "handler": create_metrics_handler(store),
        "render": lambda: render_prometheus_metrics(store),
        "service": service,
    }


test_api = {
    "create_prometheus_metric_store": create_prometheus_metric_store,
    "record_diagnostic_event": record_diagnostic_event,
    "render_prometheus_metrics": render_prometheus_metrics,
}
__test__ = test_api

__all__ = [
    "__test__",
    "create_diagnostics_prometheus_exporter",
    "create_prometheus_metric_store",
    "record_diagnostic_event",
    "render_prometheus_metrics",
    "test_api",
]
