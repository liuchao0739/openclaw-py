"""Tests for offsetless zoned datetime parsing."""

import pytest

from openclaw.infra.format_time.parse_offsetless_zoned_datetime import (
    is_offsetless_iso_date_time,
    parse_offsetless_iso_date_time_in_time_zone,
)


class TestIsOffsetlessIsoDateTime:
    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            ("2026-03-23T23:00:00", True),
            ("2026-03-23T23:00:00+02:00", False),
            ("+20m", False),
        ],
    )
    def test_detects_offsetless_iso_datetime(self, value: str, expected: bool) -> None:
        assert is_offsetless_iso_date_time(value) is expected


class TestParseOffsetlessIsoDateTimeInTimeZone:
    @pytest.mark.parametrize(
        ("raw", "time_zone", "expected"),
        [
            ("2026-03-23T23:00:00", "Europe/Oslo", "2026-03-23T22:00:00.000Z"),
            ("2026-03-29T01:30:00", "Europe/Oslo", "2026-03-29T00:30:00.000Z"),
            ("2026-03-29T02:30:00", "Europe/Oslo", None),
            ("2026-03-23T23:00:00+02:00", "Europe/Oslo", None),
            ("2026-03-23T23:00:00", "Invalid/Timezone", None),
            ("2026-03-23T23:00:00.250", "UTC", "2026-03-23T23:00:00.250Z"),
            ("2026-03-23T23:00:00.999", "UTC", "2026-03-23T23:00:00.999Z"),
            ("2026-03-23T23:00:00.123", "Europe/Oslo", "2026-03-23T22:00:00.123Z"),
        ],
    )
    def test_parses_zoned_datetime(
        self,
        raw: str,
        time_zone: str,
        expected: str | None,
    ) -> None:
        assert parse_offsetless_iso_date_time_in_time_zone(raw, time_zone) == expected
