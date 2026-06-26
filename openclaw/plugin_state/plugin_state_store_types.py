"""Plugin state store types and test seed helpers.

Mirrors src/plugin-state/plugin-state-store.types.ts and test-helpers.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any


@dataclass
class PluginStateEntry:
    """A plugin state store entry."""

    plugin_id: str
    namespace: str
    key: str
    value: Any = None
    created_at: int | None = None
    expires_at: int | None = None


@dataclass
class PluginStateSeedEntry:
    """A test seed entry for plugin state."""

    plugin_id: str
    namespace: str
    key: str
    value: Any = None
    created_at: int | None = None
    expires_at: int | None = None


def serialize_plugin_state_value(value: Any) -> str:
    """Serialize a plugin state value to JSON."""
    return json.dumps(value, ensure_ascii=False)


def deserialize_plugin_state_value(value_json: str) -> Any:
    """Deserialize a plugin state value from JSON."""
    try:
        return json.loads(value_json)
    except (json.JSONDecodeError, TypeError):
        return None


def seed_plugin_state_entries_for_tests(
    entries: list[PluginStateSeedEntry],
) -> list[dict[str, Any]]:
    """Seed plugin state entries for tests, returning serialized records."""
    if not entries:
        return []
    result: list[dict[str, Any]] = []
    for entry in entries:
        value_json = serialize_plugin_state_value(entry.value)
        record: dict[str, Any] = {
            "pluginId": entry.plugin_id,
            "namespace": entry.namespace,
            "key": entry.key,
            "valueJson": value_json,
        }
        if entry.created_at is not None:
            record["createdAt"] = entry.created_at
        if entry.expires_at is not None:
            record["expiresAt"] = entry.expires_at
        result.append(record)
    return result
