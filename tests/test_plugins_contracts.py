"""Tests for plugins/contracts shared module."""

from openclaw.plugins.contracts.shared import unique_strings


def test_basic():
    assert unique_strings(["a", "b", "a", "c"]) == ["a", "b", "c"]

def test_none():
    assert unique_strings(None) == []

def test_empty():
    assert unique_strings([]) == []

def test_normalize():
    result = unique_strings(["A", "a", "B"], normalize=str.lower)
    assert result == ["a", "b"]

def test_preserves_order():
    assert unique_strings(["c", "a", "b", "a"]) == ["c", "a", "b"]

def test_filters_empty_after_normalize():
    result = unique_strings(["x", "  ", "y"], normalize=str.strip)
    assert result == ["x", "y"]

def test_non_string_filtered():
    assert unique_strings(["a", 123, "b", None]) == ["a", "b"]

def test_custom_normalize():
    result = unique_strings(["Hello", "hello", "World"], normalize=lambda s: s.lower())
    assert result == ["hello", "world"]
