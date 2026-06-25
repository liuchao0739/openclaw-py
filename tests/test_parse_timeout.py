"""Tests for cli/parse_timeout — timeout parsing."""

from __future__ import annotations

import pytest

from openclaw.cli.parse_timeout import (
    parse_timeout_ms,
    parse_timeout_ms_with_fallback,
)


class TestParseTimeoutMs:
    def test_valid_string(self):
        assert parse_timeout_ms("30000") == 30000

    def test_valid_int(self):
        assert parse_timeout_ms(5000) == 5000

    def test_none(self):
        assert parse_timeout_ms(None) is None

    def test_empty_string(self):
        assert parse_timeout_ms("") is None
        assert parse_timeout_ms("  ") is None

    def test_zero(self):
        assert parse_timeout_ms("0") is None
        assert parse_timeout_ms(0) is None

    def test_negative(self):
        assert parse_timeout_ms("-5") is None
        assert parse_timeout_ms(-1) is None

    def test_non_numeric(self):
        assert parse_timeout_ms("abc") is None

    def test_bool(self):
        assert parse_timeout_ms(True) is None
        assert parse_timeout_ms(False) is None


class TestParseTimeoutMsWithFallback:
    def test_none_returns_fallback(self):
        assert parse_timeout_ms_with_fallback(None, 10000) == 10000

    def test_valid_value(self):
        assert parse_timeout_ms_with_fallback("30000", 10000) == 30000

    def test_empty_returns_fallback(self):
        assert parse_timeout_ms_with_fallback("", 10000) == 10000
        assert parse_timeout_ms_with_fallback("  ", 10000) == 10000

    def test_invalid_type_fallback(self):
        assert parse_timeout_ms_with_fallback([], 10000) == 10000

    def test_invalid_type_error(self):
        with pytest.raises(ValueError, match="Invalid --timeout"):
            parse_timeout_ms_with_fallback([], 10000, invalid_type="error")

    def test_empty_error(self):
        with pytest.raises(ValueError, match="Invalid --timeout"):
            parse_timeout_ms_with_fallback("", 10000, invalid_type="error")

    def test_non_numeric_raises(self):
        with pytest.raises(ValueError, match="Invalid --timeout"):
            parse_timeout_ms_with_fallback("abc", 10000)

    def test_int_input(self):
        assert parse_timeout_ms_with_fallback(5000, 10000) == 5000

    def test_zero_raises(self):
        with pytest.raises(ValueError, match="Invalid --timeout"):
            parse_timeout_ms_with_fallback("0", 10000)
