"""Tests for normalization-core number coercion."""

from __future__ import annotations

import math

from openclaw_packages.normalization_core.number_coercion import (
    MAX_TIMER_TIMEOUT_MS,
    MAX_TIMER_TIMEOUT_SECONDS,
    add_timer_timeout_grace_ms,
    as_date_timestamp_ms,
    as_finite_number,
    as_finite_number_in_range,
    as_safe_integer_in_range,
    clamp_positive_timer_timeout_ms,
    clamp_timer_timeout_ms,
    finite_seconds_to_timer_safe_milliseconds,
    is_future_date_timestamp_ms,
    non_negative_seconds_to_safe_milliseconds,
    parse_finite_number,
    parse_strict_finite_number,
    parse_strict_integer,
    parse_strict_non_negative_integer,
    parse_strict_positive_integer,
    positive_seconds_to_safe_milliseconds,
    resolve_date_timestamp_ms,
    resolve_expires_at_ms_from_duration_ms,
    resolve_expires_at_ms_from_duration_or_epoch,
    resolve_expires_at_ms_from_duration_seconds,
    resolve_expires_at_ms_from_epoch_seconds,
    resolve_integer_option,
    resolve_non_negative_integer_option,
    resolve_optional_integer_option,
    resolve_positive_timer_timeout_ms,
    resolve_timer_timeout_ms,
    resolve_timestamp_ms_to_iso_string,
    timestamp_ms_to_iso_file_stamp,
    timestamp_ms_to_iso_string,
)


def test_as_finite_number_accepts_only_finite_numbers() -> None:
    assert as_finite_number(4) == 4
    assert as_finite_number("4") is None
    assert as_finite_number(math.nan) is None
    assert as_finite_number(math.inf) is None


def test_as_finite_number_in_range_enforces_inclusive_and_exclusive_bounds() -> None:
    assert as_finite_number_in_range(0.5, min_value=0.5, max_value=2) == 0.5
    assert as_finite_number_in_range(2, min_value=0.5, max_value=2) == 2
    assert as_finite_number_in_range(0.5, min_value=0.5, min_exclusive=True) is None
    assert as_finite_number_in_range(10, max_value=10, max_exclusive=True) is None
    assert as_finite_number_in_range("1", min_value=0, max_value=2) is None


def test_as_safe_integer_in_range_accepts_only_safe_integers_inside_inclusive_bounds() -> None:
    assert as_safe_integer_in_range(-1, min_value=-1, max_value=10) == -1
    assert as_safe_integer_in_range(10, min_value=-1, max_value=10) == 10
    assert as_safe_integer_in_range(1.5, min_value=-1, max_value=10) is None
    assert as_safe_integer_in_range(11, min_value=-1, max_value=10) is None
    assert as_safe_integer_in_range(math.nan, min_value=-1, max_value=10) is None


def test_parse_finite_number_accepts_finite_numbers_and_numeric_strings() -> None:
    assert parse_finite_number(4) == 4
    assert parse_finite_number("4.5") == 4.5
    assert parse_finite_number("4.5ms") is None
    assert parse_finite_number("") is None
    assert parse_finite_number("nope") is None


def test_parse_strict_integer_accepts_only_safe_integer_tokens() -> None:
    assert parse_strict_integer("42") == 42
    assert parse_strict_integer(" -7 ") == -7
    assert parse_strict_integer("+9") == 9
    assert parse_strict_integer("1.5") is None
    assert parse_strict_integer("1e3") is None
    assert parse_strict_integer(2**53) is None


def test_parse_strict_finite_number_rejects_partial_numeric_strings() -> None:
    assert parse_strict_finite_number("42") == 42
    assert parse_strict_finite_number(".5") == 0.5
    assert parse_strict_finite_number("1e3") == 1000
    assert parse_strict_finite_number("3.14ms") is None
    assert parse_strict_finite_number("0x10") is None


def test_strict_integer_range_helpers_enforce_sign() -> None:
    assert parse_strict_positive_integer("9") == 9
    assert parse_strict_positive_integer("0") is None
    assert parse_strict_non_negative_integer("0") == 0
    assert parse_strict_non_negative_integer("-1") is None


def test_timer_timeout_helpers_centralize_node_safe_bounds() -> None:
    assert MAX_TIMER_TIMEOUT_SECONDS == 2_147_000
    assert finite_seconds_to_timer_safe_milliseconds(1.5) == 1_500
    assert finite_seconds_to_timer_safe_milliseconds(1.5, floor_seconds=True) == 1_000
    assert finite_seconds_to_timer_safe_milliseconds(10_000_000) == MAX_TIMER_TIMEOUT_MS
    assert finite_seconds_to_timer_safe_milliseconds("10") is None
    assert finite_seconds_to_timer_safe_milliseconds(math.inf) is None
    assert clamp_timer_timeout_ms(0, 10) == 10
    assert clamp_timer_timeout_ms(10_000_000_000) == MAX_TIMER_TIMEOUT_MS
    assert clamp_timer_timeout_ms(math.nan) is None
    assert clamp_positive_timer_timeout_ms(0) is None
    assert clamp_positive_timer_timeout_ms(-1) is None
    assert clamp_positive_timer_timeout_ms(10_000_000_000) == MAX_TIMER_TIMEOUT_MS
    assert resolve_positive_timer_timeout_ms(0, 5000) == 5000
    assert resolve_positive_timer_timeout_ms(2**53 - 1, 5000) == MAX_TIMER_TIMEOUT_MS
    assert resolve_timer_timeout_ms(math.nan, 5000) == 5000
    assert resolve_timer_timeout_ms(math.nan, 0, 0) == 0
    assert resolve_timer_timeout_ms(math.nan, math.inf, 25) == 25
    assert resolve_timer_timeout_ms(2**53 - 1, 5000) == MAX_TIMER_TIMEOUT_MS
    assert add_timer_timeout_grace_ms(10_000) == 15_000
    assert add_timer_timeout_grace_ms(10_000, 500) == 10_500
    assert add_timer_timeout_grace_ms(MAX_TIMER_TIMEOUT_MS - 100, 500) == MAX_TIMER_TIMEOUT_MS
    assert add_timer_timeout_grace_ms(1.7976931348623157e308) == MAX_TIMER_TIMEOUT_MS
    assert add_timer_timeout_grace_ms(math.nan) is None


def test_seconds_helpers_reject_unsafe_millisecond_values() -> None:
    assert positive_seconds_to_safe_milliseconds("10") == 10_000
    assert positive_seconds_to_safe_milliseconds("0") is None
    assert positive_seconds_to_safe_milliseconds("1e309") is None
    assert non_negative_seconds_to_safe_milliseconds("0") == 0
    assert non_negative_seconds_to_safe_milliseconds("-1") is None


def test_timestamp_iso_helper_rejects_date_invalid_timestamps() -> None:
    assert as_date_timestamp_ms(0) == 0
    assert as_date_timestamp_ms(8_640_000_000_000_000) == 8_640_000_000_000_000
    assert as_date_timestamp_ms(8_640_000_000_000_001) is None
    assert as_date_timestamp_ms(math.inf) is None
    assert as_date_timestamp_ms("0") is None
    assert timestamp_ms_to_iso_string(0) == "1970-01-01T00:00:00.000Z"
    assert timestamp_ms_to_iso_string(8_640_000_000_000_000) == "+275760-09-13T00:00:00.000Z"
    assert timestamp_ms_to_iso_string(8_640_000_000_000_001) is None
    assert timestamp_ms_to_iso_string(math.inf) is None
    assert timestamp_ms_to_iso_string("0") is None


def test_future_timestamp_helper_rejects_invalid_date_timestamps() -> None:
    assert is_future_date_timestamp_ms(1_001, now_ms=1_000) is True
    assert is_future_date_timestamp_ms(1_000, now_ms=1_000) is False
    assert is_future_date_timestamp_ms(999, now_ms=1_000) is False
    assert is_future_date_timestamp_ms(8_640_000_000_000_001, now_ms=1_000) is False
    assert is_future_date_timestamp_ms(1_001, now_ms=math.nan) is False


def test_timestamp_fallback_helpers_resolve_date_invalid_timestamps() -> None:
    assert resolve_date_timestamp_ms(1_000) == 1_000
    assert resolve_date_timestamp_ms(math.inf, 1_000) == 1_000
    assert resolve_date_timestamp_ms(math.inf, math.nan) == 0
    assert resolve_timestamp_ms_to_iso_string(0) == "1970-01-01T00:00:00.000Z"
    assert resolve_timestamp_ms_to_iso_string(math.inf, 1_000) == "1970-01-01T00:00:01.000Z"
    assert resolve_timestamp_ms_to_iso_string(math.inf, math.nan) == "1970-01-01T00:00:00.000Z"
    assert timestamp_ms_to_iso_file_stamp(1_771_850_096_000) == "2026-02-23T12-34-56.000Z"
    assert (
        timestamp_ms_to_iso_file_stamp(9_000_000_000_000_000, 1_000) == "1970-01-01T00-00-01.000Z"
    )


def test_expiry_helpers_resolve_safe_absolute_timestamps() -> None:
    assert resolve_expires_at_ms_from_duration_ms(600_000, now_ms=1_000) == 601_000
    assert resolve_expires_at_ms_from_duration_ms(600_000, now_ms=8_640_000_000_000_000) is None
    assert resolve_expires_at_ms_from_duration_ms(600_000, now_ms=8_640_000_000_000_001) is None
    assert (
        resolve_expires_at_ms_from_duration_seconds(
            "3600",
            now_ms=1_000,
            buffer_ms=300,
        )
        == 3_600_700
    )
    assert (
        resolve_expires_at_ms_from_duration_seconds(
            "10",
            now_ms=1_000,
            buffer_ms=20_000,
            min_remaining_ms=30_000,
        )
        == 31_000
    )
    assert resolve_expires_at_ms_from_duration_seconds("3600", now_ms=8_640_000_000_000_000) is None
    assert resolve_expires_at_ms_from_duration_seconds("1e309", now_ms=1_000) is None
    assert resolve_expires_at_ms_from_epoch_seconds(1234.9) == 1_234_000
    assert resolve_expires_at_ms_from_epoch_seconds("3600", buffer_ms=300) == 3_599_700
    assert resolve_expires_at_ms_from_epoch_seconds("100", max_ms=99_999) is None
    assert resolve_expires_at_ms_from_epoch_seconds(2**53 - 1) is None
    assert resolve_expires_at_ms_from_epoch_seconds(8_640_000_000_001) is None
    assert resolve_expires_at_ms_from_epoch_seconds("1e309") is None


def test_mixed_expiry_helper_handles_relative_seconds_epoch_seconds_and_absolute_ms() -> None:
    assert resolve_expires_at_ms_from_duration_or_epoch(86_400, now_ms=1_700_000_000_000) == (
        1_700_086_400_000
    )
    assert resolve_expires_at_ms_from_duration_or_epoch(1_700_000_000) == 1_700_000_000_000
    assert resolve_expires_at_ms_from_duration_or_epoch(1_700_000_000_000) == 1_700_000_000_000
    assert resolve_expires_at_ms_from_duration_or_epoch(8_640_000_000_000_001) is None
    assert resolve_expires_at_ms_from_duration_or_epoch(math.inf) is None
    assert resolve_expires_at_ms_from_duration_or_epoch(2**53) is None


def test_integer_option_helpers_floor_finite_values_and_fall_back_for_non_finite_values() -> None:
    assert resolve_integer_option(7.9, 1, min_value=1, max_value=10) == 7
    assert resolve_integer_option(math.nan, 4.9, min_value=1) == 4
    assert resolve_integer_option(-math.inf, 4, min_value=1) == 4
    assert resolve_integer_option(-4, 1, min_value=0) == 0
    assert resolve_integer_option(40, 1, max_value=10) == 10
    assert resolve_non_negative_integer_option(math.nan, 3.9) == 3


def test_optional_integer_option_helper_rejects_non_finite_values() -> None:
    assert resolve_optional_integer_option(7.9, min_value=1, max_value=10) == 7
    assert resolve_optional_integer_option(math.nan, min_value=1) is None
    assert resolve_optional_integer_option(math.inf, min_value=1) is None
    assert resolve_optional_integer_option(-4, min_value=0) == 0
    assert resolve_optional_integer_option(40, max_value=10) == 10
