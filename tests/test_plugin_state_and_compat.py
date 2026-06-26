"""Tests for plugin-state and plugins/compat modules."""

from openclaw.plugin_state.plugin_state_store_types import (
    PluginStateEntry,
    PluginStateSeedEntry,
    serialize_plugin_state_value,
    deserialize_plugin_state_value,
    seed_plugin_state_entries_for_tests,
)
from openclaw.plugins.compat.types import PluginCompatRecord


class TestPluginState:
    def test_entry_creation(self):
        entry = PluginStateEntry(plugin_id="p1", namespace="ns", key="k", value={"a": 1})
        assert entry.plugin_id == "p1"
        assert entry.value == {"a": 1}

    def test_serialize_value(self):
        assert serialize_plugin_state_value({"a": 1}) == '{"a": 1}'

    def test_deserialize_value(self):
        assert deserialize_plugin_state_value('{"a": 1}') == {"a": 1}

    def test_deserialize_invalid(self):
        assert deserialize_plugin_state_value("not json") is None

    def test_seed_entries(self):
        entries = [
            PluginStateSeedEntry(plugin_id="p1", namespace="ns", key="k1", value="v1"),
            PluginStateSeedEntry(plugin_id="p2", namespace="ns", key="k2", value={"x": 1}),
        ]
        result = seed_plugin_state_entries_for_tests(entries)
        assert len(result) == 2
        assert result[0]["pluginId"] == "p1"
        assert result[0]["valueJson"] == '"v1"'
        assert result[1]["valueJson"] == '{"x": 1}'

    def test_seed_empty(self):
        assert seed_plugin_state_entries_for_tests([]) == []

    def test_seed_with_timestamps(self):
        entry = PluginStateSeedEntry(
            plugin_id="p", namespace="ns", key="k", value="v",
            created_at=1000, expires_at=2000,
        )
        result = seed_plugin_state_entries_for_tests([entry])
        assert result[0]["createdAt"] == 1000
        assert result[0]["expiresAt"] == 2000


class TestPluginCompatRecord:
    def test_creation(self):
        record = PluginCompatRecord(
            code="PLUGIN_DEPRECATED",
            status="deprecated",
            owner="core",
            introduced="1.0.0",
            docs_path="/docs/deprecated",
        )
        assert record.code == "PLUGIN_DEPRECATED"
        assert record.status == "deprecated"
        assert record.surfaces == []

    def test_with_all_fields(self):
        record = PluginCompatRecord(
            code="X", status="removed", owner="channel",
            introduced="1.0", docs_path="/docs",
            deprecated="2.0", warning_starts="2.5",
            remove_after="3.0", replacement="newX",
            surfaces=["cli", "api"], diagnostics=["warn"],
            tests=["test1"], release_note="Removed X",
        )
        assert record.replacement == "newX"
        assert len(record.surfaces) == 2
        assert record.release_note == "Removed X"
