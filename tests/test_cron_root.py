"""Tests for cron root modules."""

import pytest

from openclaw.cron.run_id import create_cron_execution_id
from openclaw.cron.schedule_number import coerce_finite_schedule_number
from openclaw.cron.normalize_job_identity import normalize_cron_job_identity_fields
from openclaw.cron.webhook_url import normalize_http_webhook_url


class TestRunId:
    def test_basic(self):
        assert create_cron_execution_id("job-1", 1700000000) == "cron:job-1:1700000000"

    def test_empty_job_id(self):
        assert create_cron_execution_id("", 0) == "cron::0"


class TestScheduleNumber:
    def test_integer(self):
        assert coerce_finite_schedule_number(5) == 5.0

    def test_float(self):
        assert coerce_finite_schedule_number(3.14) == 3.14

    def test_bool_rejected(self):
        assert coerce_finite_schedule_number(True) is None

    def test_string_rejected(self):
        assert coerce_finite_schedule_number("5") is None

    def test_none_rejected(self):
        assert coerce_finite_schedule_number(None) is None

    def test_nan_rejected(self):
        assert coerce_finite_schedule_number(float("nan")) is None

    def test_inf_rejected(self):
        assert coerce_finite_schedule_number(float("inf")) is None


class TestNormalizeJobIdentity:
    def test_id_present_no_job_id(self):
        raw = {"id": "abc"}
        result = normalize_cron_job_identity_fields(raw)
        assert result == {"mutated": False, "legacy_job_id_issue": False}
        assert raw == {"id": "abc"}

    def test_id_empty_job_id_present(self):
        raw = {"id": "", "jobId": "legacy"}
        result = normalize_cron_job_identity_fields(raw)
        assert result["mutated"] is True
        assert result["legacy_job_id_issue"] is True
        assert raw["id"] == "legacy"
        assert "jobId" not in raw

    def test_id_missing_job_id_present(self):
        raw = {"jobId": "legacy"}
        result = normalize_cron_job_identity_fields(raw)
        assert result["mutated"] is True
        assert result["legacy_job_id_issue"] is True
        assert raw["id"] == "legacy"
        assert "jobId" not in raw

    def test_both_present_id_wins(self):
        raw = {"id": "canonical", "jobId": "legacy"}
        result = normalize_cron_job_identity_fields(raw)
        assert result["mutated"] is True  # jobId key removed
        assert result["legacy_job_id_issue"] is True
        assert raw["id"] == "canonical"
        assert "jobId" not in raw

    def test_both_empty(self):
        raw = {"id": "", "jobId": ""}
        result = normalize_cron_job_identity_fields(raw)
        assert result["mutated"] is True  # jobId key removed
        assert result["legacy_job_id_issue"] is True
        assert raw.get("id") == ""
        assert "jobId" not in raw

    def test_whitespace_id(self):
        raw = {"id": "  ", "jobId": "legacy"}
        result = normalize_cron_job_identity_fields(raw)
        assert result["mutated"] is True
        assert raw["id"] == "legacy"


class TestWebhookUrl:
    def test_valid_https(self):
        assert normalize_http_webhook_url("https://example.com/hook") == "https://example.com/hook"

    def test_valid_http(self):
        assert normalize_http_webhook_url("http://localhost:8080/hook") == "http://localhost:8080/hook"

    def test_trims_whitespace(self):
        assert normalize_http_webhook_url("  https://example.com  ") == "https://example.com"

    def test_rejects_empty(self):
        assert normalize_http_webhook_url("") is None
        assert normalize_http_webhook_url("   ") is None

    def test_rejects_non_string(self):
        assert normalize_http_webhook_url(123) is None
        assert normalize_http_webhook_url(None) is None

    def test_rejects_ftp(self):
        assert normalize_http_webhook_url("ftp://example.com") is None

    def test_rejects_file(self):
        assert normalize_http_webhook_url("file:///etc/passwd") is None

    def test_rejects_no_scheme(self):
        assert normalize_http_webhook_url("example.com/hook") is None

    def test_rejects_malformed(self):
        assert normalize_http_webhook_url("https://[invalid") is None
