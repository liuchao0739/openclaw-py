"""Tests for normalization-core string coercion."""

from __future__ import annotations

from openclaw_packages.normalization_core.string_coerce import normalize_stringified_entries


def test_normalizes_primitive_stringified_entries() -> None:
    assert normalize_stringified_entries([" a ", 42, True, 0, "", "  ", None, {}]) == [
        "a",
        "42",
        "true",
        "0",
    ]
    assert normalize_stringified_entries(None) == []
