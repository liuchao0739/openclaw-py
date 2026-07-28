from __future__ import annotations

import json
import os
import re
import time
import threading
from collections import OrderedDict
from collections.abc import Callable
from typing import Any

from openclaw.plugin_sdk.diagnostic_runtime import (
    DiagnosticEventMetadata,
    DiagnosticEventPayload,
    DiagnosticTraceContext,
    is_valid_diagnostic_span_id,
    is_valid_diagnostic_trace_flags,
    is_valid_diagnostic_trace_id,
)
from openclaw.plugin_sdk.plugin_entry import (
    OpenClawPluginService,
    OpenClawPluginServiceContext,
)
from openclaw.plugin_sdk.security_runtime import redact_sensitive_text

DEFAULT_SERVICE_NAME = "openclaw"
DROPPED_OTEL_ATTRIBUTE_KEYS = frozenset([
    "openclaw.callId", "openclaw.call_id",
    "openclaw.chatId", "openclaw.chat_id",
    "openclaw.messageId", "openclaw.message_id",
    "openclaw.parentSpanId", "openclaw.parent_span_id",
    "openclaw.runId", "openclaw.run_id",
    "openclaw.sessionId", "openclaw.session_id",
    "openclaw.sessionKey", "openclaw.session_key",
    "openclaw.spanId", "openclaw.span_id",
    "openclaw.toolCallId", "openclaw.tool_call_id",
    "openclaw.traceId", "openclaw.trace_id",
])
LOW_CARDINALITY_VALUE_RE = re.compile(r'^[A-Za-z0-9_.:-]{1,120}$')
SECURITY_TARGET_NAME_VALUE_RE = re.compile(r'^[A-Za-z0-9@/_.:-]{1,256}$')
MAX_OTEL_CONTENT_ATTRIBUTE_CHARS = 128 * 1024
MAX_OTEL_CONTENT_ARRAY_ITEMS = 200
MAX_OTEL_LOG_BODY_CHARS = 4 * 1024
MAX_OTEL_LOG_ATTRIBUTE_COUNT = 64
MAX_OTEL_LOG_ATTRIBUTE_VALUE_CHARS = 4 * 1024
LOG_RECORD_EXPORT_FAILURE_REPORT_INTERVAL_MS = 60_000
OTEL_LOG_RAW_ATTRIBUTE_KEY_RE = re.compile(r'^[A-Za-z0-9_.:-]{1,64}$')
OTEL_LOG_ATTRIBUTE_KEY_RE = re.compile(r'^[A-Za-z0-9_.:-]{1,96}$')
BLOCKED_OTEL_LOG_ATTRIBUTE_KEYS = frozenset(["__proto__", "prototype", "constructor"])
PRELOADED_OTEL_SDK_ENV = "OPENCLAW_OTEL_PRELOADED"
OTEL_EXPORTER_OTLP_ENDPOINT_ENV = "OTEL_EXPORTER_OTLP_ENDPOINT"
OTEL_EXPORTER_OTLP_TRACES_ENDPOINT_ENV = "OTEL_EXPORTER_OTLP_TRACES_ENDPOINT"
OTEL_EXPORTER_OTLP_METRICS_ENDPOINT_ENV = "OTEL_EXPORTER_OTLP_METRICS_ENDPOINT"
OTEL_EXPORTER_OTLP_LOGS_ENDPOINT_ENV = "OTEL_EXPORTER_OTLP_LOGS_ENDPOINT"
OTEL_SEMCONV_STABILITY_OPT_IN_ENV = "OTEL_SEMCONV_STABILITY_OPT_IN"
GEN_AI_LATEST_EXPERIMENTAL_OPT_IN = "gen_ai_latest_experimental"
GEN_AI_TOKEN_USAGE_BUCKETS = [
    1, 4, 16, 64, 256, 1024, 4096, 16384, 65536, 262144, 1048576, 4194304, 16777216, 67108864,
]
GEN_AI_OPERATION_DURATION_BUCKETS = [
    0.01, 0.02, 0.04, 0.08, 0.16, 0.32, 0.64, 1.28, 2.56, 5.12, 10.24, 20.48, 40.96, 81.92,
]
MAX_RETAINED_TRUSTED_SPAN_CONTEXTS = 1024
RETAINED_TRUSTED_SPAN_CONTEXT_TIMEOUT_MS = 5_000


class OtelContentCapturePolicy:
    def __init__(self) -> None:
        self.input_messages: bool = False
        self.output_messages: bool = False
        self.tool_inputs: bool = False
        self.tool_outputs: bool = False
        self.system_prompt: bool = False
        self.tool_definitions: bool = False
        self.log_bodies: bool = False


NO_CONTENT_CAPTURE = OtelContentCapturePolicy()


def _normalize_endpoint(endpoint: str | None) -> str | None:
    if endpoint is None:
        return None
    trimmed = endpoint.strip()
    return trimmed.rstrip("/") if trimmed else None


def _resolve_otel_url(endpoint: str | None, path: str) -> str | None:
    if not endpoint:
        return None
    endpoint_no_query = endpoint.split("?", 1)[0].split("#", 1)[0]
    if re.search(r'/v1/(traces|metrics|logs)$', endpoint_no_query, re.IGNORECASE):
        return endpoint
    if re.search(r'[?#]', endpoint):
        try:
            from urllib.parse import urlparse, urlunparse
            parsed = urlparse(endpoint)
            base_path = parsed.path.rstrip("/")
            parsed = parsed._replace(path=f"{base_path}/{path}")
            return urlunparse(parsed)
        except Exception:
            pass
    return f"{endpoint.rstrip('/')}/{path}"


def _resolve_signal_otel_url(
    signal_endpoint: str | None = None,
    signal_env_endpoint: str | None = None,
    endpoint: str | None = None,
    path: str = "",
) -> str | None:
    resolved = _normalize_endpoint(signal_endpoint or signal_env_endpoint) or endpoint
    return _resolve_otel_url(resolved, path)


def _resolve_sample_rate(value: float | None) -> float | None:
    if value is None:
        return None
    if not isinstance(value, (int, float)):
        return None
    if value < 0 or value > 1:
        return None
    return float(value)


def _format_error(err: Any) -> str:
    if isinstance(err, Exception):
        return err.stack if hasattr(err, "stack") and err.stack else str(err)
    if isinstance(err, str):
        return err
    try:
        return json.dumps(err)
    except Exception:
        return str(err)


def _error_category(err: Any) -> str:
    try:
        if isinstance(err, Exception) and err.name and err.name.strip():
            return _low_cardinality_attr(err.name, "Error")
        return _low_cardinality_attr(type(err).__name__, "unknown")
    except Exception:
        return "unknown"


def _collect_nested_error_candidates(err: Any) -> list[Any]:
    queue = [err]
    seen: set[int] = set()
    candidates: list[Any] = []
    while queue:
        current = queue.pop(0)
        if current is None or id(current) in seen:
            continue
        seen.add(id(current))
        candidates.append(current)
        if isinstance(current, list):
            for item in current:
                if item is not None and id(item) not in seen:
                    queue.append(item)
            continue
        if not isinstance(current, dict):
            continue
        for nested in [current.get("cause"), current.get("reason"), current.get("original"), current.get("error")]:
            if nested is not None and id(nested) not in seen:
                queue.append(nested)
        if isinstance(current.get("errors"), list):
            for nested in current["errors"]:
                if nested is not None and id(nested) not in seen:
                    queue.append(nested)
    return candidates


def _read_error_name(err: Any) -> str | None:
    if not err or not isinstance(err, dict):
        return None
    name = err.get("name")
    return name.strip() if isinstance(name, str) and name.strip() else None


def _read_error_code(err: Any) -> str | int | None:
    if not err or not isinstance(err, dict):
        return None
    code = err.get("code")
    return code if isinstance(code, (str, int)) else None


def _find_otlp_exporter_error(reason: Any) -> dict | None:
    for candidate in _collect_nested_error_candidates(reason):
        if _read_error_name(candidate) == "OTLPExporterError" and isinstance(candidate, dict):
            return candidate
    return None


def _redact_otel_attributes(attributes: dict[str, str | int | float | bool]) -> dict[str, str | int | float | bool]:
    result: dict[str, str | int | float | bool] = {}
    for key, value in attributes.items():
        if key in DROPPED_OTEL_ATTRIBUTE_KEYS:
            continue
        result[key] = redact_sensitive_text(value) if isinstance(value, str) else value
    return result


def _low_cardinality_attr(value: str | None, fallback: str = "unknown") -> str:
    if not value:
        return fallback
    redacted = redact_sensitive_text(value.strip())
    lowered = redacted.lower()
    if lowered.startswith("agent:") or ":agent:" in lowered:
        return fallback
    return redacted if LOW_CARDINALITY_VALUE_RE.match(redacted) else fallback


def _security_target_name_attr(value: str | None, fallback: str = "unknown") -> str:
    if not value:
        return fallback
    redacted = redact_sensitive_text(value.strip())
    lowered = redacted.lower()
    if lowered.startswith("agent:") or ":agent:" in lowered:
        return fallback
    return redacted if SECURITY_TARGET_NAME_VALUE_RE.match(redacted) else fallback


def _low_cardinality_queue_lane_attr(value: str | None, fallback: str = "unknown") -> str:
    if not value:
        return fallback
    redacted = redact_sensitive_text(value.strip())
    lowered = redacted.lower()
    if lowered.startswith("agent:"):
        return fallback
    colon_idx = redacted.find(":")
    lane = redacted[:colon_idx] if colon_idx >= 0 else redacted
    return lane if LOW_CARDINALITY_VALUE_RE.match(lane) else fallback


def _has_otel_semconv_opt_in(value: str | None, opt_in: str) -> bool:
    if not value:
        return False
    parts = [p.strip() for p in value.split(",")]
    return opt_in in parts


def _emit_latest_gen_ai_semconv() -> bool:
    return _has_otel_semconv_opt_in(
        os.environ.get(OTEL_SEMCONV_STABILITY_OPT_IN_ENV),
        GEN_AI_LATEST_EXPERIMENTAL_OPT_IN,
    )


def _gen_ai_operation_name(api: str | None) -> str:
    normalized = (api or "").strip().lower()
    if not normalized:
        return "chat"
    if normalized == "completions" or normalized.endswith("-completions"):
        return "text_completion"
    if normalized == "generate_content" or "generative-ai" in normalized:
        return "generate_content"
    return "chat"


def _positive_finite_number(value: int | float | None) -> int | float | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if not isinstance(value, (int, float)):
        return None
    import math
    if math.isfinite(value) and value > 0:
        return value
    return None


def _assign_positive_number_attr(attrs: dict[str, Any], key: str, value: int | float | None) -> None:
    normalized = _positive_finite_number(value)
    if normalized is not None:
        attrs[key] = normalized


def _assign_model_call_size_timing_attrs(attrs: dict[str, Any], evt: dict[str, Any]) -> None:
    _assign_positive_number_attr(attrs, "openclaw.model_call.request_bytes", evt.get("requestPayloadBytes"))
    _assign_positive_number_attr(attrs, "openclaw.model_call.response_bytes", evt.get("responseStreamBytes"))
    _assign_positive_number_attr(attrs, "openclaw.model_call.time_to_first_byte_ms", evt.get("timeToFirstByteMs"))


def _assign_gen_ai_span_identity_attrs(attrs: dict[str, Any], input_data: dict[str, str | None]) -> None:
    if _emit_latest_gen_ai_semconv():
        attrs["gen_ai.provider.name"] = _low_cardinality_attr(input_data.get("provider"))
    else:
        attrs["gen_ai.system"] = _low_cardinality_attr(input_data.get("provider"))
    if input_data.get("model"):
        attrs["gen_ai.request.model"] = redact_sensitive_text(input_data["model"].strip())
    attrs["gen_ai.operation.name"] = _gen_ai_operation_name(input_data.get("api"))


def _model_call_span_name(evt: dict[str, str | None]) -> str:
    if not _emit_latest_gen_ai_semconv():
        return "openclaw.model.call"
    return f"{_gen_ai_operation_name(evt.get('api'))} {_low_cardinality_attr(evt.get('model'))}"


def _serialize_for_otel(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (list, tuple)):
        return [_serialize_for_otel(item) for item in value[:MAX_OTEL_CONTENT_ARRAY_ITEMS]]
    if isinstance(value, dict):
        return {str(k): _serialize_for_otel(v) for k, v in list(value.items())[:MAX_OTEL_CONTENT_ARRAY_ITEMS]}
    return str(value)[:MAX_OTEL_CONTENT_ATTRIBUTE_CHARS]


def _truncate_otel_string(value: str, max_chars: int = MAX_OTEL_CONTENT_ATTRIBUTE_CHARS) -> str:
    if len(value) <= max_chars:
        return value
    return value[:max_chars]


def _sanitize_log_attribute_key(key: str) -> str | None:
    if not isinstance(key, str):
        return None
    if key in BLOCKED_OTEL_LOG_ATTRIBUTE_KEYS:
        return None
    sanitized = re.sub(r'[^A-Za-z0-9_.:-]', '_', key)
    if not OTEL_LOG_ATTRIBUTE_KEY_RE.match(sanitized):
        return None
    return sanitized


def _sanitize_log_attributes(attributes: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in attributes.items():
        sanitized_key = _sanitize_log_attribute_key(key)
        if sanitized_key is None:
            continue
        if isinstance(value, str):
            sanitized_value = _truncate_otel_string(redact_sensitive_text(value), MAX_OTEL_LOG_ATTRIBUTE_VALUE_CHARS)
            result[sanitized_key] = sanitized_value
        elif isinstance(value, bool):
            result[sanitized_key] = value
        elif isinstance(value, int):
            result[sanitized_key] = int(min(max(value, -(2**63)), 2**63 - 1))
        elif isinstance(value, float):
            import math
            if math.isfinite(value):
                result[sanitized_key] = float(value)
        if len(result) >= MAX_OTEL_LOG_ATTRIBUTE_COUNT:
            break
    return result


def _build_log_record(
    body: str,
    severity_text: str = "INFO",
    severity_number: int = 9,
    attributes: dict[str, Any] | None = None,
    trace_id: str | None = None,
    span_id: str | None = None,
    trace_flags: int | None = None,
) -> dict[str, Any]:
    return {
        "timestamp": int(time.time() * 1_000_000_000),
        "severity_text": severity_text,
        "severity_number": severity_number,
        "body": _truncate_otel_string(body, MAX_OTEL_LOG_BODY_CHARS),
        "attributes": _sanitize_log_attributes(attributes or {}),
        "trace_id": trace_id,
        "span_id": span_id,
        "trace_flags": trace_flags,
    }


class _OtelState:
    def __init__(self) -> None:
        self.initialized = False
        self.sdk: Any = None
        self.tracer_provider: Any = None
        self.meter_provider: Any = None
        self.logger_provider: Any = None
        self.tracer: Any = None
        self.meter: Any = None
        self.logger: Any = None
        self.trace_exporter: Any = None
        self.metric_exporter: Any = None
        self.log_exporter: Any = None
        self.span_processors: list[Any] = []
        self.metric_reader: Any = None
        self._lock = threading.Lock()
        self._retained_trusted_spans: OrderedDict[str, tuple[DiagnosticTraceContext, float]] = OrderedDict()
        self._unsubscribe: Callable[[], None] | None = None
        self._last_export_failure_report: dict[str, float] = {}
        self._policy = NO_CONTENT_CAPTURE
        self._log_exporter_mode: str = "otlp"
        self._service_name: str = DEFAULT_SERVICE_NAME
        self._running = False


def _init_otel_sdk(state: _OtelState, ctx: OpenClawPluginServiceContext) -> None:
    with state._lock:
        if state.initialized:
            return
        state.initialized = True

    service_name = os.environ.get("OTEL_SERVICE_NAME", DEFAULT_SERVICE_NAME)
    state._service_name = service_name

    preloaded = os.environ.get(PRELOADED_OTEL_SDK_ENV, "").strip().lower()
    if preloaded in ("1", "true", "yes"):
        ctx.logger.info("diagnostics-otel: preloaded OTel SDK detected, using existing provider")
        return

    try:
        from opentelemetry import trace as otel_trace, metrics as otel_metrics
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.sdk.metrics import MeterProvider
        from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
        from opentelemetry.sdk._logs import LoggerProvider
        from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
        from opentelemetry.semconv.resource import ResourceAttributes

        resource = Resource.create({
            ResourceAttributes.SERVICE_NAME: service_name,
        })

        state.tracer_provider = TracerProvider(resource=resource)

        trace_endpoint = _resolve_signal_otel_url(
            signal_endpoint=os.environ.get(OTEL_EXPORTER_OTLP_TRACES_ENDPOINT_ENV),
            signal_env_endpoint=os.environ.get(OTEL_EXPORTER_OTLP_ENDPOINT_ENV),
            path="v1/traces",
        )

        if trace_endpoint:
            try:
                from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
                state.trace_exporter = OTLPSpanExporter(endpoint=trace_endpoint)
                state.span_processors.append(BatchSpanProcessor(state.trace_exporter))
                ctx.logger.info(f"diagnostics-otel: traces exporting to {trace_endpoint}")
            except Exception as e:
                ctx.logger.error(f"diagnostics-otel: failed to create trace exporter: {e}")

        for proc in state.span_processors:
            state.tracer_provider.add_span_processor(proc)
        otel_trace.set_tracer_provider(state.tracer_provider)
        state.tracer = otel_trace.get_tracer("openclaw")

        metric_endpoint = _resolve_signal_otel_url(
            signal_endpoint=os.environ.get(OTEL_EXPORTER_OTLP_METRICS_ENDPOINT_ENV),
            signal_env_endpoint=os.environ.get(OTEL_EXPORTER_OTLP_ENDPOINT_ENV),
            path="v1/metrics",
        )

        if metric_endpoint:
            try:
                from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
                state.metric_exporter = OTLPMetricExporter(endpoint=metric_endpoint)
                state.metric_reader = PeriodicExportingMetricReader(
                    exporter=state.metric_exporter,
                    export_interval_millis=60_000,
                )
                state.meter_provider = MeterProvider(resource=resource, metric_readers=[state.metric_reader])
                otel_metrics.set_meter_provider(state.meter_provider)
                state.meter = otel_metrics.get_meter("openclaw")
                ctx.logger.info(f"diagnostics-otel: metrics exporting to {metric_endpoint}")
            except Exception as e:
                ctx.logger.error(f"diagnostics-otel: failed to create metric exporter: {e}")

        log_endpoint = _resolve_signal_otel_url(
            signal_endpoint=os.environ.get(OTEL_EXPORTER_OTLP_LOGS_ENDPOINT_ENV),
            signal_env_endpoint=os.environ.get(OTEL_EXPORTER_OTLP_ENDPOINT_ENV),
            path="v1/logs",
        )

        if log_endpoint:
            try:
                from opentelemetry.exporter.otlp.proto.grpc.log_exporter import OTLPLogExporter
                from opentelemetry.sdk._logs import LogRecord
                state.log_exporter = OTLPLogExporter(endpoint=log_endpoint)
                state.logger_provider = LoggerProvider(resource=resource)
                state.logger_provider.add_log_record_processor(
                    BatchLogRecordProcessor(state.log_exporter)
                )
                state.logger = state.logger_provider.get_logger("openclaw")
                ctx.logger.info(f"diagnostics-otel: logs exporting to {log_endpoint}")
            except Exception as e:
                ctx.logger.error(f"diagnostics-otel: failed to create log exporter: {e}")

        if state.tracer_provider is None and state.meter_provider is None and state.logger_provider is None:
            ctx.logger.warning("diagnostics-otel: no OTel exporters configured, service is a no-op")

    except ImportError as e:
        ctx.logger.error(f"diagnostics-otel: opentelemetry packages not available: {e}")
    except Exception as e:
        ctx.logger.error(f"diagnostics-otel: failed to initialize OTel SDK: {e}")


def _create_diagnostic_span_context(
    trace_id: str,
    span_id: str,
    trace_flags: int = 1,
) -> DiagnosticTraceContext:
    return {
        "traceId": trace_id,
        "spanId": span_id,
        "traceFlags": trace_flags,
    }


def _retain_trusted_span_context(state: _OtelState, ctx: DiagnosticTraceContext) -> None:
    if not is_valid_diagnostic_trace_id(ctx.get("traceId", "")):
        return
    now = time.time()
    state._retained_trusted_spans[ctx["traceId"]] = (ctx, now)
    while len(state._retained_trusted_spans) > MAX_RETAINED_TRUSTED_SPAN_CONTEXTS:
        state._retained_trusted_spans.popitem(last=False)


def _expire_retained_span_contexts(state: _OtelState) -> None:
    now = time.time()
    expired_keys = [
        k for k, (_, ts) in state._retained_trusted_spans.items()
        if (now - ts) * 1000 > RETAINED_TRUSTED_SPAN_CONTEXT_TIMEOUT_MS
    ]
    for k in expired_keys:
        state._retained_trusted_spans.pop(k, None)


def _lookup_retained_span_context(state: _OtelState, trace_id: str) -> DiagnosticTraceContext | None:
    _expire_retained_span_contexts(state)
    entry = state._retained_trusted_spans.get(trace_id)
    if entry is None:
        return None
    return entry[0]


def _build_log_record_for_event(
    evt: dict[str, Any],
    metadata: DiagnosticEventMetadata,
    state: _OtelState,
) -> dict[str, Any] | None:
    if not metadata.get("trusted", False):
        return None

    trace_context = metadata.get("traceContext")
    if trace_context is None:
        trace_id = evt.get("traceId") or evt.get("trace_id")
        span_id = evt.get("spanId") or evt.get("span_id")
        if trace_id:
            retained = _lookup_retained_span_context(state, trace_id)
            if retained:
                trace_context = retained

    attributes = {
        "openclaw.event.type": _low_cardinality_attr(evt.get("type")),
        "openclaw.event.trusted": "true",
    }

    if evt.get("sessionId"):
        attributes["openclaw.session.id"] = _low_cardinality_attr(evt["sessionId"])
    if evt.get("runId"):
        attributes["openclaw.run.id"] = _low_cardinality_attr(evt["runId"])
    if evt.get("agentId"):
        attributes["openclaw.agent.id"] = _low_cardinality_attr(evt["agentId"])
    if evt.get("channel"):
        attributes["openclaw.channel"] = _low_cardinality_attr(evt["channel"])

    body_text = json.dumps(_serialize_for_otel(evt))
    log_record = _build_log_record(
        body=body_text,
        severity_text="INFO",
        severity_number=9,
        attributes=attributes,
        trace_id=trace_context.get("traceId") if trace_context else None,
        span_id=trace_context.get("spanId") if trace_context else None,
        trace_flags=trace_context.get("traceFlags") if trace_context else None,
    )
    return log_record


def _emit_log_record(state: _OtelState, log_record: dict[str, Any]) -> None:
    try:
        if state.logger is not None:
            state.logger.emit(log_record)
    except Exception:
        pass

    if state._log_exporter_mode in ("stdout", "both"):
        try:
            line = {
                "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "signal": "openclaw.diagnostic.log",
                "service.name": state._service_name,
                "severityText": log_record["severity_text"],
                "severityNumber": log_record["severity_number"],
                "body": log_record["body"],
                "attributes": log_record["attributes"],
            }
            if log_record.get("trace_id"):
                line["trace_id"] = log_record["trace_id"]
            if log_record.get("span_id"):
                line["span_id"] = log_record["span_id"]
            import sys
            sys.stdout.write(json.dumps(line) + "\n")
        except Exception:
            pass


def _record_model_call_span(
    state: _OtelState,
    evt: dict[str, Any],
    metadata: DiagnosticEventMetadata,
) -> None:
    if state.tracer is None:
        return

    trace_id = None
    span_id = None
    trace_flags = 1

    parent_ctx = metadata.get("traceContext")
    if parent_ctx:
        trace_id = parent_ctx.get("traceId")
        span_id = parent_ctx.get("spanId")
        trace_flags = parent_ctx.get("traceFlags", 1)
    else:
        raw_trace_id = evt.get("traceId") or evt.get("trace_id")
        if raw_trace_id and is_valid_diagnostic_trace_id(raw_trace_id):
            retained = _lookup_retained_span_context(state, raw_trace_id)
            if retained:
                trace_id = retained.get("traceId")
                span_id = retained.get("spanId")
                trace_flags = retained.get("traceFlags", 1)

    attrs: dict[str, Any] = {}
    _assign_gen_ai_span_identity_attrs(attrs, {
        "api": evt.get("api"),
        "model": evt.get("model"),
        "provider": evt.get("provider"),
    })
    _assign_model_call_size_timing_attrs(attrs, evt)

    if evt.get("type") == "model.call.error":
        attrs["openclaw.error.category"] = _error_category(evt.get("error"))

    span_name = _model_call_span_name(evt)
    duration_ms = evt.get("durationMs")

    try:
        span = state.tracer.start_span(
            span_name,
            attributes=attrs,
        )

        if trace_id and span_id:
            try:
                from opentelemetry.trace import SpanContext
                span._context = SpanContext(
                    trace_id=trace_id,
                    span_id=span_id,
                    is_remote=True,
                    trace_flags=trace_flags,
                )
            except Exception:
                pass

        if duration_ms is not None:
            span.set_attribute("openclaw.duration_ms", duration_ms)

        if evt.get("type") == "model.call.error":
            span.set_status("ERROR", _error_category(evt.get("error")))
        else:
            span.set_status("OK")

        span.end()

        new_ctx = _create_diagnostic_span_context(
            trace_id=trace_id or "",
            span_id=span.get_span_context().span_id,
            trace_flags=trace_flags,
        )
        _retain_trusted_span_context(state, new_ctx)
    except Exception:
        pass


def _record_model_call_metrics(
    state: _OtelState,
    evt: dict[str, Any],
    metadata: DiagnosticEventMetadata,
) -> None:
    if state.meter is None:
        return

    if not metadata.get("trusted", False):
        return

    provider = _low_cardinality_attr(evt.get("provider"))
    model = _low_cardinality_attr(evt.get("model"))
    operation = _gen_ai_operation_name(evt.get("api"))
    outcome = "error" if evt.get("type") == "model.call.error" else "completed"

    try:
        duration_histogram = state.meter.create_histogram(
            "openclaw.model.call.duration",
            unit="s",
            description="Model call duration in seconds.",
        )
        duration_histogram.record(
            (evt.get("durationMs") or 0) / 1000,
            {
                "openclaw.provider": provider,
                "openclaw.model": model,
                "openclaw.operation": operation,
                "openclaw.outcome": outcome,
            },
        )
    except Exception:
        pass

    try:
        call_counter = state.meter.create_counter(
            "openclaw.model.call.count",
            description="Model call count by outcome.",
        )
        call_counter.add(
            1,
            {
                "openclaw.provider": provider,
                "openclaw.model": model,
                "openclaw.operation": operation,
                "openclaw.outcome": outcome,
            },
        )
    except Exception:
        pass

    usage = evt.get("usage") or {}
    for token_type, attr_name in [
        ("input", "input_tokens"),
        ("output", "output_tokens"),
        ("cacheRead", "cache_read_input_tokens"),
        ("cacheWrite", "cache_creation_input_tokens"),
    ]:
        value = usage.get(token_type)
        if value and isinstance(value, (int, float)):
            try:
                histogram = state.meter.create_histogram(
                    f"gen_ai.client.token.{attr_name}",
                    unit="tokens",
                    description=f"GenAI {attr_name} token usage.",
                )
                histogram.record(
                    value,
                    {
                        "gen_ai.system": provider,
                        "gen_ai.request.model": model,
                    },
                )
            except Exception:
                pass


def _record_tool_execution_span(
    state: _OtelState,
    evt: dict[str, Any],
    metadata: DiagnosticEventMetadata,
) -> None:
    if state.tracer is None:
        return

    tool_name = _low_cardinality_attr(evt.get("toolName"), "tool")
    tool_owner = _low_cardinality_attr(evt.get("toolOwner"), "none")
    tool_source = _low_cardinality_attr(evt.get("toolSource"), "core")
    outcome = "error" if evt.get("type") == "tool.execution.error" else "completed"

    attrs: dict[str, Any] = {
        "openclaw.tool.name": tool_name,
        "openclaw.tool.owner": tool_owner,
        "openclaw.tool.source": tool_source,
        "openclaw.outcome": outcome,
    }

    if evt.get("type") == "tool.execution.error":
        attrs["openclaw.error.category"] = _low_cardinality_attr(evt.get("errorCategory"), "other")

    duration_ms = evt.get("durationMs")

    try:
        span = state.tracer.start_span(f"openclaw.tool.{tool_name}", attributes=attrs)

        if duration_ms is not None:
            span.set_attribute("openclaw.duration_ms", duration_ms)

        if outcome == "error":
            span.set_status("ERROR", _low_cardinality_attr(evt.get("errorCategory"), "other"))
        else:
            span.set_status("OK")

        span.end()
    except Exception:
        pass


def _record_tool_execution_metrics(
    state: _OtelState,
    evt: dict[str, Any],
    metadata: DiagnosticEventMetadata,
) -> None:
    if state.meter is None:
        return
    if not metadata.get("trusted", False):
        return

    tool_name = _low_cardinality_attr(evt.get("toolName"), "tool")
    tool_owner = _low_cardinality_attr(evt.get("toolOwner"), "none")
    tool_source = _low_cardinality_attr(evt.get("toolSource"), "core")
    outcome = "error" if evt.get("type") == "tool.execution.error" else "completed"

    labels = {
        "openclaw.tool.name": tool_name,
        "openclaw.tool.owner": tool_owner,
        "openclaw.tool.source": tool_source,
        "openclaw.outcome": outcome,
    }

    try:
        duration_histogram = state.meter.create_histogram(
            "openclaw.tool.execution.duration",
            unit="s",
            description="Tool execution duration in seconds.",
        )
        duration_histogram.record(
            (evt.get("durationMs") or 0) / 1000,
            labels,
        )
    except Exception:
        pass

    try:
        counter = state.meter.create_counter(
            "openclaw.tool.execution.count",
            description="Tool execution count by outcome.",
        )
        counter.add(1, labels)
    except Exception:
        pass


def _record_run_span(
    state: _OtelState,
    evt: dict[str, Any],
    metadata: DiagnosticEventMetadata,
) -> None:
    if state.tracer is None:
        return

    agent_id = _low_cardinality_attr(evt.get("agentId"))
    outcome = _low_cardinality_attr(evt.get("outcome"), "unknown")

    attrs: dict[str, Any] = {
        "openclaw.agent.id": agent_id,
        "openclaw.outcome": outcome,
        "openclaw.channel": _low_cardinality_attr(evt.get("channel")),
    }

    duration_ms = evt.get("durationMs")

    try:
        span = state.tracer.start_span("openclaw.run", attributes=attrs)
        if duration_ms is not None:
            span.set_attribute("openclaw.duration_ms", duration_ms)
        if outcome in ("error", "timeout", "cancelled"):
            span.set_status("ERROR", outcome)
        else:
            span.set_status("OK")
        span.end()
    except Exception:
        pass


def _record_run_metrics(
    state: _OtelState,
    evt: dict[str, Any],
    metadata: DiagnosticEventMetadata,
) -> None:
    if state.meter is None:
        return
    if not metadata.get("trusted", False):
        return

    outcome = _low_cardinality_attr(evt.get("outcome"), "unknown")
    agent_id = _low_cardinality_attr(evt.get("agentId"))
    channel = _low_cardinality_attr(evt.get("channel"))

    labels = {
        "openclaw.outcome": outcome,
        "openclaw.agent.id": agent_id,
        "openclaw.channel": channel,
    }

    try:
        duration_histogram = state.meter.create_histogram(
            "openclaw.run.duration",
            unit="s",
            description="Agent run duration in seconds.",
        )
        duration_histogram.record(
            (evt.get("durationMs") or 0) / 1000,
            labels,
        )
    except Exception:
        pass

    try:
        counter = state.meter.create_counter(
            "openclaw.run.count",
            description="Agent run count by outcome.",
        )
        counter.add(1, labels)
    except Exception:
        pass


def _record_harness_run_span(
    state: _OtelState,
    evt: dict[str, Any],
    metadata: DiagnosticEventMetadata,
) -> None:
    if state.tracer is None:
        return

    harness_id = _low_cardinality_attr(evt.get("harnessId"))
    phase = _low_cardinality_attr(evt.get("phase"))
    outcome = _low_cardinality_attr(evt.get("outcome"))

    attrs: dict[str, Any] = {
        "openclaw.harness.id": harness_id,
        "openclaw.harness.phase": phase,
        "openclaw.outcome": outcome,
    }

    duration_ms = evt.get("durationMs")

    try:
        span = state.tracer.start_span("openclaw.harness.run", attributes=attrs)
        if duration_ms is not None:
            span.set_attribute("openclaw.duration_ms", duration_ms)
        if outcome == "error":
            span.set_status("ERROR", _low_cardinality_attr(evt.get("errorCategory"), "other"))
        else:
            span.set_status("OK")
        span.end()
    except Exception:
        pass


def _record_diagnostic_event(
    state: _OtelState,
    evt: DiagnosticEventPayload,
    metadata: DiagnosticEventMetadata,
) -> None:
    if not metadata.get("trusted", False):
        return

    evt_type = evt.get("type", "")

    if evt_type == "model.call.completed" or evt_type == "model.call.error":
        _record_model_call_span(state, evt, metadata)
        _record_model_call_metrics(state, evt, metadata)

    elif evt_type == "model.usage":
        _record_model_call_metrics(state, evt, metadata)

    elif evt_type == "tool.execution.completed" or evt_type == "tool.execution.error":
        _record_tool_execution_span(state, evt, metadata)
        _record_tool_execution_metrics(state, evt, metadata)

    elif evt_type == "run.completed":
        _record_run_span(state, evt, metadata)
        _record_run_metrics(state, evt, metadata)

    elif evt_type == "harness.run.completed" or evt_type == "harness.run.error":
        _record_harness_run_span(state, evt, metadata)

    log_record = _build_log_record_for_event(evt, metadata, state)
    if log_record is not None:
        _emit_log_record(state, log_record)


def _start_service(state: _OtelState, ctx: OpenClawPluginServiceContext) -> None:
    if state._running:
        return
    state._running = True

    _init_otel_sdk(state, ctx)

    if state.tracer is None and state.meter is None and state.logger is None:
        ctx.logger.warning("diagnostics-otel: OTel not initialized, events will be dropped")

    subscribe = None
    internal_diag = ctx.get("internal_diagnostics")
    if isinstance(internal_diag, dict):
        subscribe = internal_diag.get("onEvent")

    if subscribe is None:
        ctx.logger.error("diagnostics-otel: internal diagnostics capability unavailable")
        state._running = False
        return

    def _on_event(evt: DiagnosticEventPayload, metadata: DiagnosticEventMetadata) -> None:
        try:
            _record_diagnostic_event(state, evt, metadata)
        except Exception as err:
            ctx.logger.error(f"diagnostics-otel: event handler failed ({evt.get('type', '?')}): {err}")

    state._unsubscribe = subscribe(_on_event)

    if isinstance(internal_diag, dict) and internal_diag.get("emit"):
        internal_diag.emit({
            "type": "telemetry.exporter",
            "exporter": "diagnostics-otel",
            "signal": "traces",
            "status": "started",
            "reason": "configured",
        })


def _stop_service(state: _OtelState, ctx: OpenClawPluginServiceContext) -> None:
    if not state._running:
        return
    state._running = False

    if state._unsubscribe is not None:
        state._unsubscribe()
        state._unsubscribe = None

    try:
        if state.tracer_provider is not None:
            state.tracer_provider.shutdown()
    except Exception:
        pass

    try:
        if state.meter_provider is not None:
            state.meter_provider.shutdown()
    except Exception:
        pass

    try:
        if state.logger_provider is not None:
            state.logger_provider.shutdown()
    except Exception:
        pass

    ctx.logger.info("diagnostics-otel: service stopped")


def create_diagnostics_otel_service() -> OpenClawPluginService:
    state = _OtelState()

    service: OpenClawPluginService = {
        "id": "diagnostics-otel",
        "start": lambda ctx: _start_service(state, ctx),
        "stop": lambda ctx: _stop_service(state, ctx),
    }

    return service