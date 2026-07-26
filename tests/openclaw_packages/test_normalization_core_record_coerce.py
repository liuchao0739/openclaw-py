"""Tests for normalization-core record coercion."""

from __future__ import annotations

from openclaw_packages.normalization_core.record_coerce import (
    as_nullable_record,
    as_optional_record,
)


def test_keeps_record_coercion_behavior_for_optional_and_nullable_variants() -> None:
    assert as_optional_record({"ok": True}) == {"ok": True}
    assert as_optional_record(None) is None
    assert as_optional_record([{"ok": True}]) is None
    assert as_nullable_record({"ok": True}) == {"ok": True}
    assert as_nullable_record(None) is None
    assert as_nullable_record([{"ok": True}]) is None
