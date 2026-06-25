"""Tests for cli/cron_cli — thread id parsing and session target normalization."""

from __future__ import annotations

import pytest

from openclaw.cli.cron_cli import (
    normalize_cron_session_target_option,
    parse_cron_thread_id_option,
)


class TestParseThreadId:
    def test_valid_integer(self):
        assert parse_cron_thread_id_option("123") == 123

    def test_valid_integer_from_int(self):
        assert parse_cron_thread_id_option(456) == 456

    def test_none(self):
        assert parse_cron_thread_id_option(None) is None

    def test_empty(self):
        assert parse_cron_thread_id_option("") is None

    def test_non_numeric(self):
        with pytest.raises(ValueError, match="positive integer"):
            parse_cron_thread_id_option("abc")

    def test_zero(self):
        with pytest.raises(ValueError, match="safe positive"):
            parse_cron_thread_id_option("0")

    def test_negative(self):
        with pytest.raises(ValueError, match="positive integer"):
            parse_cron_thread_id_option("-5")


class TestNormalizeSessionTarget:
    def test_main(self):
        assert normalize_cron_session_target_option("main") == "main"

    def test_isolated(self):
        assert normalize_cron_session_target_option("isolated") == "isolated"

    def test_current(self):
        assert normalize_cron_session_target_option("current") == "current"

    def test_case_insensitive(self):
        assert normalize_cron_session_target_option("MAIN") == "main"

    def test_session_id(self):
        assert normalize_cron_session_target_option("session:abc-123") == "session:abc-123"

    def test_session_empty_id(self):
        assert normalize_cron_session_target_option("session:") is None

    def test_unknown(self):
        assert normalize_cron_session_target_option("unknown") is None

    def test_none(self):
        assert normalize_cron_session_target_option(None) is None

    def test_empty(self):
        assert normalize_cron_session_target_option("") is None
