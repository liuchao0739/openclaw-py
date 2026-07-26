"""Diagnostic flag/event helpers for plugins that want narrow runtime gating.

Mirrors src/plugin-sdk/diagnostic-runtime.ts.
"""

from __future__ import annotations

from openclaw.infra.diagnostic_events import (
    DiagnosticEventMetadata,
    DiagnosticEventPayload,
    DiagnosticEventPrivateData,
    DiagnosticModelCallContent,
    emit_diagnostic_event,
    is_internal_diagnostic_event_metadata,
    on_diagnostic_event,
    reset_diagnostic_events_for_test,
    wait_for_diagnostic_events_drained,
)
from openclaw.infra.diagnostic_trace_context import (
    DiagnosticTraceContext,
    create_child_diagnostic_trace_context,
    create_diagnostic_trace_context,
    create_diagnostic_trace_context_from_active_scope,
    format_diagnostic_traceparent,
    freeze_diagnostic_trace_context,
    is_valid_diagnostic_span_id,
    is_valid_diagnostic_trace_flags,
    is_valid_diagnostic_trace_id,
    parse_diagnostic_traceparent,
)

__all__ = [
    "DiagnosticEventMetadata",
    "DiagnosticEventPayload",
    "DiagnosticEventPrivateData",
    "DiagnosticModelCallContent",
    "DiagnosticTraceContext",
    "create_child_diagnostic_trace_context",
    "create_diagnostic_trace_context",
    "create_diagnostic_trace_context_from_active_scope",
    "emit_diagnostic_event",
    "format_diagnostic_traceparent",
    "freeze_diagnostic_trace_context",
    "is_internal_diagnostic_event_metadata",
    "is_valid_diagnostic_span_id",
    "is_valid_diagnostic_trace_flags",
    "is_valid_diagnostic_trace_id",
    "on_diagnostic_event",
    "parse_diagnostic_traceparent",
    "reset_diagnostic_events_for_test",
    "wait_for_diagnostic_events_drained",
]
