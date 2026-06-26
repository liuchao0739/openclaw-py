"""Tests for normalization-core string coercion."""

from openclaw.packages.normalization_core import (
    read_string_value,
    normalize_nullable_string,
    normalize_optional_string,
    normalize_stringified_optional_string,
    normalize_stringified_entries,
    normalize_optional_lowercase_string,
    normalize_lowercase_string_or_empty,
    normalize_fast_mode,
    resolve_primary_string_value,
    normalize_optional_thread_value,
    normalize_optional_stringified_id,
    has_non_empty_string,
)


def test_read_string_value():
    assert read_string_value("hello") == "hello"
    assert read_string_value(123) is None

def test_normalize_nullable_string():
    assert normalize_nullable_string("  hello  ") == "hello"
    assert normalize_nullable_string("") is None
    assert normalize_nullable_string(123) is None

def test_normalize_optional_string():
    assert normalize_optional_string("x") == "x"
    assert normalize_optional_string("") is None

def test_normalize_stringified_optional_string():
    assert normalize_stringified_optional_string("x") == "x"
    assert normalize_stringified_optional_string(42) == "42"
    assert normalize_stringified_optional_string(True) == "true"
    assert normalize_stringified_optional_string(float("nan")) is None

def test_normalize_stringified_entries():
    assert normalize_stringified_entries(["a", 1, "b", None]) == ["a", "1", "b"]
    assert normalize_stringified_entries([]) == []

def test_normalize_optional_lowercase_string():
    assert normalize_optional_lowercase_string("  Hello  ") == "hello"
    assert normalize_optional_lowercase_string("") is None

def test_normalize_lowercase_string_or_empty():
    assert normalize_lowercase_string_or_empty("HELLO") == "hello"
    assert normalize_lowercase_string_or_empty("") == ""
    assert normalize_lowercase_string_or_empty(None) == ""

def test_normalize_fast_mode():
    assert normalize_fast_mode(True) is True
    assert normalize_fast_mode(False) is False
    assert normalize_fast_mode("off") is False
    assert normalize_fast_mode("enabled") is True
    assert normalize_fast_mode("auto") == "auto"
    assert normalize_fast_mode(None) is None
    assert normalize_fast_mode("bogus") is None

def test_resolve_primary_string_value():
    assert resolve_primary_string_value("x") == "x"
    assert resolve_primary_string_value({"primary": "y"}) == "y"
    assert resolve_primary_string_value({"primary": ""}) is None
    assert resolve_primary_string_value(123) is None

def test_normalize_optional_thread_value():
    assert normalize_optional_thread_value(42) == 42
    assert normalize_optional_thread_value("thread-1") == "thread-1"
    assert normalize_optional_thread_value(float("inf")) is None
    assert normalize_optional_thread_value(True) is None

def test_normalize_optional_stringified_id():
    assert normalize_optional_stringified_id(42) == "42"
    assert normalize_optional_stringified_id("x") == "x"
    assert normalize_optional_stringified_id(None) is None

def test_has_non_empty_string():
    assert has_non_empty_string("x") is True
    assert has_non_empty_string("  ") is False
    assert has_non_empty_string(123) is False
