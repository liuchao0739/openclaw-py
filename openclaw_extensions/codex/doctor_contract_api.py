import copy
from typing import Any, List


def _as_record(value: Any):
    if isinstance(value, dict) and not isinstance(value, list):
        return value
    return None


def _has_retired_dynamic_tools_profile(value: Any) -> bool:
    record = _as_record(value) or {}
    return "codexDynamicToolsProfile" in record


def _has_legacy_plugin_destructive_policy(value: Any) -> bool:
    codex_plugins = _as_record(value)
    if not codex_plugins:
        return False
    if codex_plugins.get("allow_destructive_actions") == "on-request":
        return True
    plugins = _as_record(codex_plugins.get("plugins"))
    if not plugins:
        return False
    for plugin in plugins.values():
        plugin_record = _as_record(plugin)
        if plugin_record and plugin_record.get("allow_destructive_actions") == "on-request":
            return True
    return False


legacy_config_rules: List[dict] = [
    {
        "path": ["plugins", "entries", "codex", "config"],
        "message": 'plugins.entries.codex.config.codexDynamicToolsProfile is retired; Codex app-server always keeps Codex-native workspace tools native. Run "openclaw doctor --fix".',
        "match": _has_retired_dynamic_tools_profile,
    },
    {
        "path": ["plugins", "entries", "codex", "config", "codexPlugins"],
        "message": 'plugins.entries.codex.config.codexPlugins.allow_destructive_actions="on-request" was renamed to "auto". Run "openclaw doctor --fix".',
        "match": _has_legacy_plugin_destructive_policy,
    },
]


def normalize_compatibility_config(params: dict) -> dict:
    cfg = params["cfg"]
    plugins = cfg.get("plugins") if isinstance(cfg, dict) else None
    entries = plugins.get("entries") if isinstance(plugins, dict) else None
    codex_entry = entries.get("codex") if isinstance(entries, dict) else None
    raw_entry = _as_record(codex_entry)
    raw_plugin_config = _as_record(raw_entry.get("config") if raw_entry else None)
    raw_codex_plugins = _as_record(raw_plugin_config.get("codexPlugins") if raw_plugin_config else None)
    should_remove_dynamic_tools_profile = raw_plugin_config is not None and _has_retired_dynamic_tools_profile(raw_plugin_config)
    should_rewrite_destructive_policy = _has_legacy_plugin_destructive_policy(raw_codex_plugins)
    if not raw_plugin_config or (not should_remove_dynamic_tools_profile and not should_rewrite_destructive_policy):
        return {"config": cfg, "changes": []}

    next_config = copy.deepcopy(cfg)
    next_plugins = _as_record(next_config.get("plugins"))
    next_entries = _as_record(next_plugins.get("entries") if next_plugins else None)
    next_entry = _as_record(next_entries.get("codex") if next_entries else None)
    next_plugin_config = _as_record(next_entry.get("config") if next_entry else None)
    if not next_plugin_config:
        return {"config": cfg, "changes": []}

    changes: List[str] = []
    if should_remove_dynamic_tools_profile:
        next_plugin_config.pop("codexDynamicToolsProfile", None)
        changes.append("Removed retired plugins.entries.codex.config.codexDynamicToolsProfile; Codex app-server always keeps Codex-native workspace tools native.")

    if should_rewrite_destructive_policy:
        next_codex_plugins = _as_record(next_plugin_config.get("codexPlugins"))
        if next_codex_plugins and next_codex_plugins.get("allow_destructive_actions") == "on-request":
            next_codex_plugins["allow_destructive_actions"] = "auto"
        next_plugin_policies = _as_record(next_codex_plugins.get("plugins") if next_codex_plugins else None)
        if next_plugin_policies:
            for plugin in next_plugin_policies.values():
                next_plugin = _as_record(plugin)
                if next_plugin and next_plugin.get("allow_destructive_actions") == "on-request":
                    next_plugin["allow_destructive_actions"] = "auto"
        changes.append('Renamed plugins.entries.codex.config.codexPlugins allow_destructive_actions="on-request" values to "auto".')

    return {"config": next_config, "changes": changes}


session_route_state_owners = [
    {
        "id": "codex",
        "label": "Codex",
        "providerIds": ["codex", "codex-cli", "openai-codex"],
        "runtimeIds": ["codex", "codex-cli"],
        "cliSessionKeys": ["codex-cli"],
        "authProfilePrefixes": ["codex:", "codex-cli:", "openai-codex:"],
    }
]
