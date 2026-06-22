"""Process-wide registry for native agent harness implementations."""

from __future__ import annotations

from typing import Any

from openclaw.agents.harness.types import RegisteredAgentHarness

_REGISTRY: dict[str, RegisteredAgentHarness] = {}


def register_agent_harness(
    harness: Any,
    *,
    owner_plugin_id: str | None = None,
) -> None:
    harness_id = str(getattr(harness, "id", "") or "").strip()
    if not harness_id:
        raise ValueError("harness.id is required")
    plugin_id = getattr(harness, "pluginId", None) or owner_plugin_id
    entry: RegisteredAgentHarness = {
        "harness": harness,
    }
    if owner_plugin_id is not None:
        entry["ownerPluginId"] = owner_plugin_id
    if plugin_id is not None:
        try:
            harness.pluginId = plugin_id  # type: ignore[attr-defined]
        except (AttributeError, TypeError):
            pass
    _REGISTRY[harness_id] = entry


def get_registered_agent_harness(harness_id: str) -> RegisteredAgentHarness | None:
    return _REGISTRY.get(harness_id.strip())


def get_agent_harness(harness_id: str) -> Any | None:
    entry = get_registered_agent_harness(harness_id)
    return entry["harness"] if entry else None


def list_registered_agent_harnesses() -> list[RegisteredAgentHarness]:
    return list(_REGISTRY.values())


def list_agent_harness_ids() -> list[str]:
    return list(_REGISTRY.keys())


def clear_agent_harnesses() -> None:
    _REGISTRY.clear()


def reset_agent_harness_registry_for_tests() -> None:
    clear_agent_harnesses()


def restore_registered_agent_harnesses(entries: list[RegisteredAgentHarness]) -> None:
    _REGISTRY.clear()
    for entry in entries:
        harness = entry["harness"]
        hid = str(getattr(harness, "id", "") or "").strip()
        if hid:
            _REGISTRY[hid] = entry