"""Ensures runtime plugins required by selected native harnesses are installed.

Full plugin registry, provider owner resolution, and activation context are
deferred until the plugins system is ported. This stub provides the public
function signature so harness callers can wire lifecycle without crashes.
"""

from __future__ import annotations

from typing import Any

from openclaw.agents.harness.policy import resolve_agent_harness_policy

_COLD_LOADABLE_HARNESS_PLUGIN_IDS = {"codex", "copilot"}


def _is_default_agent_runtime_id(value: str | None) -> bool:
    return value is None or value.strip().lower() in ("", "default", "auto")


def _normalize_optional_agent_runtime_id(value: str | None) -> str | None:
    if value is None:
        return None
    trimmed = str(value).strip()
    return trimmed or None


def _dedupe_plugin_ids(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        plugin_id = value.strip()
        if not plugin_id or plugin_id in seen:
            continue
        seen.add(plugin_id)
        result.append(plugin_id)
    return result


async def ensure_selected_agent_harness_plugin(params: dict[str, Any]) -> None:
    """Ensure the plugin that owns the selected harness runtime is loaded before harness selection."""
    runtime_override = _normalize_optional_agent_runtime_id(params.get("agentHarnessRuntimeOverride"))
    policy = resolve_agent_harness_policy(
        provider=params.get("provider"),
        model_id=params.get("modelId"),
        config=params.get("config"),
        agent_id=params.get("agentId"),
        session_key=params.get("sessionKey"),
    )
    runtime = runtime_override if (runtime_override and not _is_default_agent_runtime_id(runtime_override)) else policy.get("runtime", "auto")

    if _is_default_agent_runtime_id(runtime) or runtime == "openclaw" or runtime not in _COLD_LOADABLE_HARNESS_PLUGIN_IDS:
        return

    # Full plugin registry loading deferred until plugins system is ported.
