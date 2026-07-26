"""Creates and propagates lightweight W3C diagnostic trace contexts.

Mirrors src/infra/diagnostic-trace-context.ts.
"""

from __future__ import annotations

import secrets
from collections.abc import Callable
from contextvars import ContextVar
from typing import Any, TypeVar


class DiagnosticTraceContext(dict[str, str]):
    """W3C diagnostic trace context mapping."""


_TRACEPARENT_VERSION = "00"
_DEFAULT_TRACE_FLAGS = "01"
_MAX_TRACEPARENT_LENGTH = 128
_TRACE_ID_RE = __import__("re").compile(r"^[0-9a-f]{32}$")
_SPAN_ID_RE = __import__("re").compile(r"^[0-9a-f]{16}$")
_TRACE_FLAGS_RE = __import__("re").compile(r"^[0-9a-f]{2}$")
_TRACEPARENT_VERSION_RE = __import__("re").compile(r"^[0-9a-f]{2}$")

_diagnostic_trace_scope: ContextVar[DiagnosticTraceContext | None] = ContextVar(
    "openclaw_diagnostic_trace_scope",
    default=None,
)


def _random_hex(byte_count: int) -> str:
    return secrets.token_hex(byte_count)


def _is_non_zero_hex(value: str) -> bool:
    return not __import__("re").fullmatch(r"0+", value)


def _random_trace_id() -> str:
    while True:
        trace_id = _random_hex(16)
        if _is_non_zero_hex(trace_id):
            return trace_id


def _random_span_id() -> str:
    while True:
        span_id = _random_hex(8)
        if _is_non_zero_hex(span_id):
            return span_id


def is_valid_diagnostic_trace_id(value: object) -> bool:
    """Return whether a value is a non-zero W3C trace id."""
    return (
        isinstance(value, str)
        and _TRACE_ID_RE.fullmatch(value) is not None
        and _is_non_zero_hex(value)
    )


def is_valid_diagnostic_span_id(value: object) -> bool:
    """Return whether a value is a non-zero W3C span id."""
    return (
        isinstance(value, str)
        and _SPAN_ID_RE.fullmatch(value) is not None
        and _is_non_zero_hex(value)
    )


def is_valid_diagnostic_trace_flags(value: object) -> bool:
    """Return whether a value is a valid W3C trace-flags byte."""
    return isinstance(value, str) and _TRACE_FLAGS_RE.fullmatch(value) is not None


def _normalize_trace_id(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.lower()
    return normalized if is_valid_diagnostic_trace_id(normalized) else None


def _normalize_span_id(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.lower()
    return normalized if is_valid_diagnostic_span_id(normalized) else None


def _normalize_trace_flags(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.lower()
    return normalized if is_valid_diagnostic_trace_flags(normalized) else None


def parse_diagnostic_traceparent(
    traceparent: str | None,
) -> DiagnosticTraceContext | None:
    """Parse a W3C ``traceparent`` header into a normalized diagnostic trace context."""
    if not isinstance(traceparent, str) or len(traceparent) > _MAX_TRACEPARENT_LENGTH:
        return None
    parts = traceparent.strip().lower().split("-")
    if len(parts) < 4:
        return None
    version, trace_id, span_id, trace_flags = parts[:4]
    if (
        _TRACEPARENT_VERSION_RE.fullmatch(version) is None
        or version == "ff"
        or (version == _TRACEPARENT_VERSION and len(parts) != 4)
    ):
        return None
    normalized_trace_id = _normalize_trace_id(trace_id)
    normalized_span_id = _normalize_span_id(span_id)
    normalized_trace_flags = _normalize_trace_flags(trace_flags)
    if not normalized_trace_id or not normalized_span_id or not normalized_trace_flags:
        return None
    return {
        "traceId": normalized_trace_id,
        "spanId": normalized_span_id,
        "traceFlags": normalized_trace_flags,
    }


def format_diagnostic_traceparent(
    context: DiagnosticTraceContext | None,
) -> str | None:
    """Format a diagnostic trace context as a W3C ``traceparent`` header."""
    if not context or not context.get("spanId"):
        return None
    trace_id = _normalize_trace_id(context.get("traceId"))
    span_id = _normalize_span_id(context.get("spanId"))
    trace_flags = _normalize_trace_flags(context.get("traceFlags")) or _DEFAULT_TRACE_FLAGS
    if not trace_id or not span_id:
        return None
    return f"{_TRACEPARENT_VERSION}-{trace_id}-{span_id}-{trace_flags}"


def create_diagnostic_trace_context(
    *,
    trace_id: str | None = None,
    span_id: str | None = None,
    parent_span_id: str | None = None,
    trace_flags: str | None = None,
    traceparent: str | None = None,
    **legacy_kwargs: Any,
) -> DiagnosticTraceContext:
    """Create a normalized trace context from explicit fields, traceparent, or generated ids."""
    if legacy_kwargs:
        trace_id = legacy_kwargs.get("traceId", trace_id)
        span_id = legacy_kwargs.get("spanId", span_id)
        parent_span_id = legacy_kwargs.get("parentSpanId", parent_span_id)
        trace_flags = legacy_kwargs.get("traceFlags", trace_flags)
        traceparent = legacy_kwargs.get("traceparent", traceparent)

    parsed = parse_diagnostic_traceparent(traceparent)
    resolved_trace_id = (
        _normalize_trace_id(trace_id) or (parsed or {}).get("traceId") or _random_trace_id()
    )
    resolved_span_id = (
        _normalize_span_id(span_id) or (parsed or {}).get("spanId") or _random_span_id()
    )
    resolved_parent_span_id = _normalize_span_id(parent_span_id)
    context: DiagnosticTraceContext = {
        "traceId": resolved_trace_id,
        "spanId": resolved_span_id,
        "traceFlags": _normalize_trace_flags(trace_flags)
        or (parsed or {}).get("traceFlags")
        or _DEFAULT_TRACE_FLAGS,
    }
    if resolved_parent_span_id and resolved_parent_span_id != resolved_span_id:
        context["parentSpanId"] = resolved_parent_span_id
    return context


def create_child_diagnostic_trace_context(
    parent: DiagnosticTraceContext,
    *,
    span_id: str | None = None,
    parent_span_id: str | None = None,
    trace_flags: str | None = None,
    **legacy_kwargs: Any,
) -> DiagnosticTraceContext:
    """Create a child context preserving the parent trace id and recording the parent span id."""
    if legacy_kwargs:
        span_id = legacy_kwargs.get("spanId", span_id)
        parent_span_id = legacy_kwargs.get("parentSpanId", parent_span_id)
        trace_flags = legacy_kwargs.get("traceFlags", trace_flags)
    resolved_parent_span_id = _normalize_span_id(parent_span_id) or _normalize_span_id(
        parent.get("spanId")
    )
    return create_diagnostic_trace_context(
        trace_id=parent["traceId"],
        span_id=span_id,
        parent_span_id=resolved_parent_span_id,
        trace_flags=trace_flags or parent.get("traceFlags"),
    )


def create_diagnostic_trace_context_from_active_scope(
    *,
    span_id: str | None = None,
    parent_span_id: str | None = None,
    trace_flags: str | None = None,
    **legacy_kwargs: Any,
) -> DiagnosticTraceContext:
    """Create a child of the active trace scope, or a new root context when none is active."""
    active = get_active_diagnostic_trace_context()
    if active is None:
        return create_diagnostic_trace_context(
            span_id=span_id,
            parent_span_id=parent_span_id,
            trace_flags=trace_flags,
            **legacy_kwargs,
        )
    return create_child_diagnostic_trace_context(
        active,
        span_id=span_id,
        parent_span_id=parent_span_id,
        trace_flags=trace_flags,
        **legacy_kwargs,
    )


def freeze_diagnostic_trace_context(context: DiagnosticTraceContext) -> DiagnosticTraceContext:
    """Return an immutable defensive copy of a trace context."""
    frozen = DiagnosticTraceContext({"traceId": context["traceId"]})
    if context.get("spanId"):
        frozen["spanId"] = context["spanId"]
    if context.get("parentSpanId"):
        frozen["parentSpanId"] = context["parentSpanId"]
    if context.get("traceFlags"):
        frozen["traceFlags"] = context["traceFlags"]
    return frozen


def get_active_diagnostic_trace_context() -> DiagnosticTraceContext | None:
    """Return the trace context bound to the current async scope."""
    return _diagnostic_trace_scope.get()


_T = TypeVar("_T")


def run_with_diagnostic_trace_context(
    trace: DiagnosticTraceContext, callback: Callable[[], _T]
) -> _T:
    """Run a callback with a frozen trace context bound to async-local storage."""
    token = _diagnostic_trace_scope.set(freeze_diagnostic_trace_context(trace))
    try:
        return callback()
    finally:
        _diagnostic_trace_scope.reset(token)


def reset_diagnostic_trace_context_for_test() -> None:
    """Clear async-local trace context state between tests."""
    _diagnostic_trace_scope.set(None)
