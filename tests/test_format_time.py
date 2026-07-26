"""Tests for infra/format-time duration and datetime formatting."""

import math
import re
from datetime import UTC, datetime

import pytest

from openclaw.infra.format_time import format_datetime as format_datetime_module
from openclaw.infra.format_time import format_relative as format_relative_module
from openclaw.infra.format_time.format_datetime import (
    format_utc_timestamp,
    format_zoned_timestamp,
    resolve_timezone,
)
from openclaw.infra.format_time.format_duration import (
    format_duration_compact,
    format_duration_human,
    format_duration_precise,
    format_duration_seconds,
)
from openclaw.infra.format_time.format_relative import (
    format_relative_timestamp,
    format_time_ago,
)

FIXED_NOW_MS = datetime(2024, 2, 10, 12, 0, 0, tzinfo=UTC).timestamp() * 1000
INVALID_DURATION_INPUTS = [None, float("nan"), -100]


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


class TestResolveTimezone:
    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            ("America/New_York", "America/New_York"),
            ("Europe/London", "Europe/London"),
            ("UTC", "UTC"),
            ("Invalid/Timezone", None),
            ("garbage", None),
            ("", None),
        ],
    )
    def test_resolve_timezone(self, value: str, expected: str | None) -> None:
        assert resolve_timezone(value) == expected


class TestFormatUtcTimestamp:
    @pytest.mark.parametrize(
        ("display_seconds", "expected"),
        [
            (False, "2024-01-15T14:30Z"),
            (True, "2024-01-15T14:30:45Z"),
        ],
    )
    def test_format_utc_timestamp(self, display_seconds: bool, expected: str) -> None:
        date = datetime(2024, 1, 15, 14, 30, 45, tzinfo=UTC)
        if display_seconds:
            assert format_utc_timestamp(date, {"display_seconds": True}) == expected
        else:
            assert format_utc_timestamp(date) == expected


class TestFormatZonedTimestamp:
    @pytest.mark.parametrize(
        ("options", "pattern"),
        [
            ({"time_zone": "UTC"}, r"2024-01-15 14:30"),
            ({"time_zone": "UTC", "display_seconds": True}, r"2024-01-15 14:30:45"),
        ],
    )
    def test_format_zoned_timestamp(self, options: dict[str, object], pattern: str) -> None:
        date = datetime(2024, 1, 15, 14, 30, 45, tzinfo=UTC)
        result = format_zoned_timestamp(date, options)
        assert result is not None
        assert re.search(pattern, result)

    def test_returns_none_when_required_parts_are_missing(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        def missing_parts(*_args: object, **_kwargs: object) -> dict[str, str | None]:
            return {
                "month": "01",
                "day": "15",
                "hour": "14",
                "minute": "30",
            }

        monkeypatch.setattr(format_datetime_module, "_get_zoned_format_parts", missing_parts)
        result = format_zoned_timestamp(
            datetime(2024, 1, 15, 14, 30, tzinfo=UTC),
            {"time_zone": "UTC"},
        )
        assert result is None

    def test_returns_none_when_formatting_throws(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        def throwing(*_args: object, **_kwargs: object) -> dict[str, str]:
            raise RuntimeError("boom")

        monkeypatch.setattr(format_datetime_module, "_get_zoned_format_parts", throwing)
        result = format_zoned_timestamp(
            datetime(2024, 1, 15, 14, 30, tzinfo=UTC),
            {"time_zone": "UTC"},
        )
        assert result is None


class TestFormatTimeAgo:
    def test_returns_fallback_for_invalid_input(self) -> None:
        for value in INVALID_DURATION_INPUTS:
            if value is None or (isinstance(value, float) and math.isnan(value)):
                assert format_time_ago(value) == "unknown"
            else:
                assert format_time_ago(value) == "unknown"
        assert format_time_ago(None, {"fallback": "n/a"}) == "n/a"

    @pytest.mark.parametrize(
        ("duration_ms", "expected"),
        [
            (0, "just now"),
            (29000, "just now"),
            (30000, "1m ago"),
            (300000, "5m ago"),
            (7200000, "2h ago"),
            (47 * 3600000, "47h ago"),
            (48 * 3600000, "2d ago"),
            (172800000, "2d ago"),
        ],
    )
    def test_format_time_ago(self, duration_ms: int, expected: str) -> None:
        assert format_time_ago(duration_ms) == expected

    @pytest.mark.parametrize(
        ("duration_ms", "expected"),
        [
            (0, "0s"),
            (300000, "5m"),
            (7200000, "2h"),
        ],
    )
    def test_omits_suffix_when_disabled(self, duration_ms: int, expected: str) -> None:
        assert format_time_ago(duration_ms, {"suffix": False}) == expected


class TestFormatRelativeTimestamp:
    @pytest.fixture(autouse=True)
    def fixed_now(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(format_relative_module, "_now_ms", lambda: FIXED_NOW_MS)

    def test_returns_fallback_for_invalid_input(self) -> None:
        assert format_relative_timestamp(None) == "n/a"
        assert format_relative_timestamp(None, {"fallback": "unknown"}) == "unknown"

    @pytest.mark.parametrize(
        ("offset_ms", "expected"),
        [
            (-10000, "just now"),
            (-30000, "just now"),
            (-300000, "5m ago"),
            (-7200000, "2h ago"),
            (-(47 * 3600000), "47h ago"),
            (-(48 * 3600000), "2d ago"),
            (30000, "in <1m"),
            (300000, "in 5m"),
            (7200000, "in 2h"),
        ],
    )
    def test_format_relative_timestamp(self, offset_ms: int, expected: str) -> None:
        assert format_relative_timestamp(FIXED_NOW_MS + offset_ms) == expected

    @pytest.mark.parametrize(
        ("offset_ms", "options", "expected"),
        [
            (
                -7 * 24 * 3600000,
                {"date_fallback": True, "timezone": "UTC"},
                "7d ago",
            ),
            (
                -8 * 24 * 3600000,
                {"date_fallback": True, "timezone": "UTC"},
                "Feb 2",
            ),
            (
                -8 * 24 * 3600000,
                {"timezone": "UTC"},
                "8d ago",
            ),
        ],
    )
    def test_date_fallback(
        self,
        offset_ms: int,
        options: dict[str, object],
        expected: str,
    ) -> None:
        assert format_relative_timestamp(FIXED_NOW_MS + offset_ms, options) == expected

    def test_falls_back_to_relative_days_when_date_formatting_fails(self) -> None:
        assert (
            format_relative_timestamp(
                FIXED_NOW_MS - 8 * 24 * 3600000,
                {"date_fallback": True, "timezone": "Invalid/Timezone"},
            )
            == "8d ago"
        )
