"""Tests for infra/format-time duration formatting."""

import math

from openclaw.infra.format_time.format_duration import (
    format_duration_seconds,
    format_duration_precise,
    format_duration_compact,
    format_duration_human,
)


class TestFormatDurationSeconds:
    def test_basic(self):
        assert format_duration_seconds(1500) == "1.5s"

    def test_zero(self):
        assert format_duration_seconds(0) == "0s"

    def test_seconds_unit(self):
        assert format_duration_seconds(5000, {"unit": "seconds"}) == "5 seconds"

    def test_decimals(self):
        assert format_duration_seconds(1234, {"decimals": 2}) == "1.23s"

    def test_trailing_zeros_trimmed(self):
        assert format_duration_seconds(2000) == "2s"

    def test_non_finite(self):
        assert format_duration_seconds(float("nan")) == "unknown"
        assert format_duration_seconds(float("inf")) == "unknown"

    def test_negative_clamped(self):
        assert format_duration_seconds(-1000) == "0s"


class TestFormatDurationPrecise:
    def test_milliseconds(self):
        assert format_duration_precise(500) == "500ms"

    def test_seconds(self):
        assert format_duration_precise(1500) == "1.5s"

    def test_non_finite(self):
        assert format_duration_precise(float("nan")) == "unknown"


class TestFormatDurationCompact:
    def test_milliseconds(self):
        assert format_duration_compact(500) == "500ms"

    def test_seconds(self):
        assert format_duration_compact(45000) == "45s"

    def test_minutes_seconds(self):
        assert format_duration_compact(125000) == "2m5s"

    def test_spaced(self):
        assert format_duration_compact(125000, {"spaced": True}) == "2m 5s"

    def test_hours_minutes(self):
        assert format_duration_compact(5400000) == "1h30m"

    def test_days_hours(self):
        assert format_duration_compact(90000000) == "1d1h"

    def test_days_only(self):
        assert format_duration_compact(172800000) == "2d"

    def test_none(self):
        assert format_duration_compact(None) is None

    def test_non_finite(self):
        assert format_duration_compact(float("inf")) is None

    def test_zero_or_negative(self):
        assert format_duration_compact(0) is None
        assert format_duration_compact(-100) is None

    def test_minutes_only(self):
        assert format_duration_compact(60000) == "1m"


class TestFormatDurationHuman:
    def test_milliseconds(self):
        assert format_duration_human(500) == "500ms"

    def test_seconds(self):
        assert format_duration_human(5000) == "5s"

    def test_minutes(self):
        assert format_duration_human(180000) == "3m"

    def test_hours(self):
        assert format_duration_human(7200000) == "2h"

    def test_days(self):
        assert format_duration_human(432000000) == "5d"

    def test_none(self):
        assert format_duration_human(None) == "n/a"

    def test_custom_fallback(self):
        assert format_duration_human(None, "—") == "—"

    def test_non_finite(self):
        assert format_duration_human(float("nan")) == "n/a"

    def test_negative(self):
        assert format_duration_human(-100) == "n/a"

    def test_zero(self):
        assert format_duration_human(0) == "0ms"
