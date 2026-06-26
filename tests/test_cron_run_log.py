"""Tests for cron/run-log entry codec."""

import pytest

from openclaw.cron.run_log.entry_codec import (
    parse_cron_run_log_entry_object,
    CRON_FAILOVER_REASONS,
    _resolve_failover_reason_from_error,
)


def _base_entry(**overrides):
    base = {
        "action": "finished",
        "jobId": "job-1",
        "ts": 1700000000,
        "status": "success",
    }
    base.update(overrides)
    return base


def test_parse_valid_minimal():
    entry = parse_cron_run_log_entry_object(_base_entry())
    assert entry is not None
    assert entry["jobId"] == "job-1"
    assert entry["action"] == "finished"
    assert entry["ts"] == 1700000000


def test_parse_non_object_returns_none():
    assert parse_cron_run_log_entry_object(None) is None
    assert parse_cron_run_log_entry_object("x") is None
    assert parse_cron_run_log_entry_object(42) is None


def test_parse_wrong_action_returns_none():
    assert parse_cron_run_log_entry_object(_base_entry(action="started")) is None


def test_parse_missing_job_id():
    e = _base_entry()
    del e["jobId"]
    assert parse_cron_run_log_entry_object(e) is None


def test_parse_empty_job_id():
    assert parse_cron_run_log_entry_object(_base_entry(jobId="  ")) is None


def test_parse_non_finite_ts():
    assert parse_cron_run_log_entry_object(_base_entry(ts=float("nan"))) is None
    assert parse_cron_run_log_entry_object(_base_entry(ts=float("inf"))) is None


def test_parse_non_numeric_ts():
    assert parse_cron_run_log_entry_object(_base_entry(ts="abc")) is None


def test_parse_job_id_filter_mismatch():
    assert parse_cron_run_log_entry_object(
        _base_entry(), {"jobId": "other-job"}
    ) is None


def test_parse_job_id_filter_match():
    entry = parse_cron_run_log_entry_object(_base_entry(), {"jobId": "job-1"})
    assert entry is not None


def test_parse_error_reason_valid():
    entry = parse_cron_run_log_entry_object(_base_entry(errorReason="timeout"))
    assert entry["errorReason"] == "timeout"


def test_parse_error_reason_invalid():
    entry = parse_cron_run_log_entry_object(_base_entry(errorReason="bogus"))
    assert entry["errorReason"] is None


def test_parse_error_reason_inferred_from_error():
    entry = parse_cron_run_log_entry_object(_base_entry(error="Request timed out"))
    assert entry["errorReason"] == "timeout"


def test_parse_error_reason_inferred_auth():
    entry = parse_cron_run_log_entry_object(_base_entry(error="401 Unauthorized"))
    assert entry["errorReason"] == "auth"


def test_parse_error_reason_inferred_rate_limit():
    entry = parse_cron_run_log_entry_object(_base_entry(error="429 rate limit exceeded"))
    assert entry["errorReason"] == "rate_limit"


def test_parse_usage_normalized():
    entry = parse_cron_run_log_entry_object(
        _base_entry(usage={"input_tokens": 100, "output_tokens": 50, "bad": "x"})
    )
    assert entry["usage"]["input_tokens"] == 100
    assert entry["usage"]["output_tokens"] == 50
    assert "bad" not in entry["usage"]


def test_parse_usage_none_when_empty():
    entry = parse_cron_run_log_entry_object(_base_entry(usage={"bad": "x"}))
    assert entry["usage"] is None


def test_parse_usage_none_when_not_object():
    entry = parse_cron_run_log_entry_object(_base_entry(usage="x"))
    assert entry["usage"] is None


def test_parse_delivered_bool():
    entry = parse_cron_run_log_entry_object(_base_entry(delivered=True))
    assert entry["delivered"] is True


def test_parse_delivery_status_valid():
    entry = parse_cron_run_log_entry_object(_base_entry(deliveryStatus="delivered"))
    assert entry["deliveryStatus"] == "delivered"


def test_parse_delivery_status_invalid():
    entry = parse_cron_run_log_entry_object(_base_entry(deliveryStatus="bogus"))
    assert "deliveryStatus" not in entry


def test_parse_failure_notification_delivery():
    entry = parse_cron_run_log_entry_object(
        _base_entry(
            failureNotificationDelivery={
                "status": "not-delivered",
                "delivered": False,
                "error": "boom",
            }
        )
    )
    fnd = entry["failureNotificationDelivery"]
    assert fnd["status"] == "not-delivered"
    assert fnd["delivered"] is False
    assert fnd["error"] == "boom"


def test_parse_failure_notification_invalid_status():
    entry = parse_cron_run_log_entry_object(
        _base_entry(failureNotificationDelivery={"status": "bogus"})
    )
    assert "failureNotificationDelivery" not in entry


def test_parse_delivery_object():
    entry = parse_cron_run_log_entry_object(
        _base_entry(delivery={"channel": "discord"})
    )
    assert entry["delivery"] == {"channel": "discord"}


def test_parse_session_id_and_key():
    entry = parse_cron_run_log_entry_object(
        _base_entry(sessionId="sess-1", sessionKey="agent:x:sess-1")
    )
    assert entry["sessionId"] == "sess-1"
    assert entry["sessionKey"] == "agent:x:sess-1"


def test_parse_empty_session_id_omitted():
    entry = parse_cron_run_log_entry_object(_base_entry(sessionId="  "))
    assert "sessionId" not in entry


def test_parse_provider_non_empty_kept():
    # Original TS keeps the raw string if non-empty after trim (does not trim it).
    entry = parse_cron_run_log_entry_object(_base_entry(provider="  anthropic  "))
    assert entry["provider"] == "  anthropic  "


def test_parse_provider_empty_omitted():
    entry = parse_cron_run_log_entry_object(_base_entry(provider="   "))
    assert entry["provider"] is None


def test_parse_model_trimmed():
    entry = parse_cron_run_log_entry_object(_base_entry(model="claude-3"))
    assert entry["model"] == "claude-3"


def test_parse_run_id_trimmed():
    entry = parse_cron_run_log_entry_object(_base_entry(runId="run-123"))
    assert entry["runId"] == "run-123"
    entry2 = parse_cron_run_log_entry_object(_base_entry(runId="   "))
    assert entry2["runId"] is None


def test_failover_reasons_set():
    assert "timeout" in CRON_FAILOVER_REASONS
    assert "auth" in CRON_FAILOVER_REASONS
    assert "bogus" not in CRON_FAILOVER_REASONS


def test_resolve_failover_none():
    assert _resolve_failover_reason_from_error(None, None) is None
    assert _resolve_failover_reason_from_error("", None) is None


def test_resolve_failover_billing():
    assert _resolve_failover_reason_from_error("402 payment required", None) == "billing"


def test_resolve_failover_overloaded():
    assert _resolve_failover_reason_from_error("529 overloaded", None) == "overloaded"


def test_resolve_failover_server_error():
    assert _resolve_failover_reason_from_error("500 server error", None) == "server_error"


def test_resolve_failover_model_not_found():
    assert _resolve_failover_reason_from_error("model not found", None) == "model_not_found"


def test_resolve_failover_session_expired():
    assert _resolve_failover_reason_from_error("session expired", None) == "session_expired"


def test_resolve_failover_empty_response():
    assert _resolve_failover_reason_from_error("empty response", None) == "empty_response"


def test_resolve_failover_unknown():
    assert _resolve_failover_reason_from_error("something weird", None) == "unknown"
