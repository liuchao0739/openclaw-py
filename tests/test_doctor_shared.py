"""Tests for commands/doctor/shared — object, allowlist, allow-from-mode, config migrate."""

from __future__ import annotations

from openclaw.commands.doctor.shared import (
    as_object_record,
    has_allow_from_entries,
    migrate_legacy_config,
    resolve_allow_from_mode,
)


class TestAsObjectRecord:
    def test_dict(self):
        assert as_object_record({"a": 1}) == {"a": 1}

    def test_none(self):
        assert as_object_record(None) is None

    def test_array(self):
        assert as_object_record([1, 2]) is None

    def test_string(self):
        assert as_object_record("hello") is None

    def test_empty_dict(self):
        assert as_object_record({}) == {}


class TestHasAllowFromEntries:
    def test_with_entries(self):
        assert has_allow_from_entries(["alice", "bob"]) is True

    def test_empty(self):
        assert has_allow_from_entries([]) is False

    def test_none(self):
        assert has_allow_from_entries(None) is False

    def test_whitespace_only(self):
        assert has_allow_from_entries(["  ", ""]) is False

    def test_with_numbers(self):
        assert has_allow_from_entries([123, "alice"]) is True


class TestResolveAllowFromMode:
    def test_default_strict(self):
        assert resolve_allow_from_mode("unknown") == "strict"


class TestMigrateLegacyConfig:
    def test_none_input(self):
        result = migrate_legacy_config(None)
        assert result["config"] is None
        assert result["changes"] == []

    def test_dict_input(self):
        result = migrate_legacy_config({"agents": {}})
        assert result["config"] is not None
