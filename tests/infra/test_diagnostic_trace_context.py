"""Tests for diagnostic trace context helpers."""

from __future__ import annotations

from openclaw.infra.diagnostic_trace_context import (
    create_child_diagnostic_trace_context,
    create_diagnostic_trace_context,
    format_diagnostic_traceparent,
    is_valid_diagnostic_span_id,
    is_valid_diagnostic_trace_id,
    parse_diagnostic_traceparent,
    reset_diagnostic_trace_context_for_test,
)


def test_parse_and_format_traceparent_round_trip() -> None:
    traceparent = "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"
    parsed = parse_diagnostic_traceparent(traceparent)
    assert parsed is not None
    assert parsed["traceId"] == "4bf92f3577b34da6a3ce929d0e0e4736"
    assert parsed["spanId"] == "00f067aa0ba902b7"
    assert format_diagnostic_traceparent(parsed) == traceparent


def test_create_child_preserves_trace_id() -> None:
    parent = create_diagnostic_trace_context(
        trace_id="4bf92f3577b34da6a3ce929d0e0e4736",
        span_id="00f067aa0ba902b7",
    )
    child = create_child_diagnostic_trace_context(parent)
    assert child["traceId"] == parent["traceId"]
    assert child["spanId"] != parent["spanId"]
    assert child["parentSpanId"] == parent["spanId"]


def test_validators_reject_zero_ids() -> None:
    assert not is_valid_diagnostic_trace_id("0" * 32)
    assert not is_valid_diagnostic_span_id("0" * 16)
    reset_diagnostic_trace_context_for_test()
