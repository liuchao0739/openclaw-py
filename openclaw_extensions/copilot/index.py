"""Copilot plugin entrypoint registers its OpenClaw integration."""

from __future__ import annotations

import math
from typing import Any

from openclaw.plugin_sdk.plugin_entry import OpenClawPluginApi, define_plugin_entry
from openclaw_extensions.copilot.harness import create_copilot_agent_harness


def _is_record(value: Any) -> bool:
    return isinstance(value, dict) and not isinstance(value, list)


def _read_pool_options(plugin_config: Any) -> dict[str, Any] | None:
    if not _is_record(plugin_config):
        return None
    pool = plugin_config.get("pool")
    if not _is_record(pool):
        return None
    idle_ttl_ms = pool.get("idleTtlMs")
    if not isinstance(idle_ttl_ms, (int, float)) or not math.isfinite(idle_ttl_ms) or idle_ttl_ms < 1:
        return None
    return {"idleTtlMs": idle_ttl_ms}


def _resolve_session_store(api: OpenClawPluginApi) -> Any:
    runtime = getattr(api, "runtime", None)
    if runtime is None:
        return None
    state = getattr(runtime, "state", None)
    if state is None:
        return None
    open_sync_keyed_store = getattr(state, "open_sync_keyed_store", None) or getattr(
        state, "openSyncKeyedStore", None
    )
    if not callable(open_sync_keyed_store):
        return None
    try:
        return open_sync_keyed_store(
            {
                "namespace": "sdk-sessions",
                "maxEntries": 5000,
                "defaultTtlMs": 90 * 24 * 60 * 60 * 1000,
            }
        )
    except Exception:
        return None


def _register(api: OpenClawPluginApi) -> None:
    pool_options = _read_pool_options(getattr(api, "plugin_config", None))
    session_store = _resolve_session_store(api)
    options: dict[str, Any] = {}
    if pool_options:
        options["poolOptions"] = pool_options
    if session_store is not None:
        options["sessionStore"] = session_store
    api.register_agent_harness(create_copilot_agent_harness(options))


default = define_plugin_entry(
    id="copilot",
    name="GitHub Copilot agent runtime",
    description="Registers the GitHub Copilot agent runtime.",
    register=_register,
)
