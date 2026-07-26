"""Doctor contract hooks for Codex plugin config migrations and session-route ownership."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from openclaw.packages.normalization_core import is_record


def _as_record(value: Any) -> dict[str, Any] | None:
    return value if is_record(value) else None


def _has_retired_dynamic_tools_profile(value: Any) -> bool:
    record = _as_record(value)
    return record is not None and "codexDynamicToolsProfile" in record


def _has_legacy_plugin_destructive_policy(value: Any) -> bool:
    codex_plugins = _as_record(value)
    if codex_plugins is None:
        return False
    if codex_plugins.get("allow_destructive_actions") == "on-request":
        return True
    plugins = _as_record(codex_plugins.get("plugins"))
    if plugins is None:
        return False
    return any(
        (_as_record(plugin) or {}).get("allow_destructive_actions") == "on-request"
        for plugin in plugins.values()
    )


legacy_config_rules: list[dict[str, Any]] = [
    {
        "path": ["plugins", "entries", "codex", "config"],
        "message": (
            'plugins.entries.codex.config.codexDynamicToolsProfile is retired; Codex app-server '
            "always keeps Codex-native workspace tools native. Run \"openclaw doctor --fix\"."
        ),
        "match": _has_retired_dynamic_tools_profile,
    },
    {
        "path": ["plugins", "entries", "codex", "config", "codexPlugins"],
        "message": (
            'plugins.entries.codex.config.codexPlugins.allow_destructive_actions="on-request" '
            'was renamed to "auto". Run "openclaw doctor --fix".'
        ),
        "match": _has_legacy_plugin_destructive_policy,
    },
]


def normalize_compatibility_config(params: dict[str, Any]) -> dict[str, Any]:
    """Remove retired Codex plugin config keys while preserving unrelated config."""
    cfg = params["cfg"]
    plugins = _as_record(cfg.get("plugins")) if is_record(cfg) else None
    entries = _as_record(plugins.get("entries")) if plugins else None
    raw_entry = _as_record(entries.get("codex")) if entries else None
    raw_plugin_config = _as_record(raw_entry.get("config")) if raw_entry else None
    raw_codex_plugins = _as_record(raw_plugin_config.get("codexPlugins")) if raw_plugin_config else None
    should_remove_dynamic_tools_profile = (
        raw_plugin_config is not None and _has_retired_dynamic_tools_profile(raw_plugin_config)
    )
    should_rewrite_destructive_policy = _has_legacy_plugin_destructive_policy(raw_codex_plugins)
    if not raw_plugin_config or (not should_remove_dynamic_tools_profile and not should_rewrite_destructive_policy):
        return {"config": cfg, "changes": []}

    next_config = deepcopy(cfg)
    next_plugins = _as_record(next_config.get("plugins"))
    next_entries = _as_record(next_plugins.get("entries")) if next_plugins else None
    next_entry = _as_record(next_entries.get("codex")) if next_entries else None
    next_plugin_config = _as_record(next_entry.get("config")) if next_entry else None
    if next_plugin_config is None:
        return {"config": cfg, "changes": []}

    changes: list[str] = []
    if should_remove_dynamic_tools_profile:
        next_plugin_config.pop("codexDynamicToolsProfile", None)
        changes.append(
            "Removed retired plugins.entries.codex.config.codexDynamicToolsProfile; "
            "Codex app-server always keeps Codex-native workspace tools native."
        )

    if should_rewrite_destructive_policy:
        next_codex_plugins = _as_record(next_plugin_config.get("codexPlugins"))
        if next_codex_plugins is not None and next_codex_plugins.get("allow_destructive_actions") == "on-request":
            next_codex_plugins["allow_destructive_actions"] = "auto"
        next_plugin_policies = _as_record(next_codex_plugins.get("plugins")) if next_codex_plugins else None
        if next_plugin_policies is not None:
            for plugin in next_plugin_policies.values():
                next_plugin = _as_record(plugin)
                if next_plugin is not None and next_plugin.get("allow_destructive_actions") == "on-request":
                    next_plugin["allow_destructive_actions"] = "auto"
        changes.append(
            'Renamed plugins.entries.codex.config.codexPlugins allow_destructive_actions="on-request" '
            'values to "auto".'
        )

    return {"config": next_config, "changes": changes}


session_route_state_owners: list[dict[str, Any]] = [
    {
        "id": "codex",
        "label": "Codex",
        "providerIds": ["codex", "codex-cli", "openai-codex"],
        "runtimeIds": ["codex", "codex-cli"],
        "cliSessionKeys": ["codex-cli"],
        "authProfilePrefixes": ["codex:", "codex-cli:", "openai-codex:"],
    }
]
