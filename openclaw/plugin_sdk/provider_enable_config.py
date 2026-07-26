"""Provider enable config helpers update provider allowlists and config enablement state."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, TypeVar

TConfig = TypeVar("TConfig", bound=dict[str, Any])


def _ensure_plugin_allowlisted(cfg: TConfig, plugin_id: str) -> TConfig:
    plugins = cfg.get("plugins")
    if not isinstance(plugins, dict):
        return cfg
    allow = plugins.get("allow")
    if not isinstance(allow, list) or plugin_id in allow:
        return cfg

    next_cfg = deepcopy(cfg)
    next_plugins = dict(next_cfg.get("plugins") or {})
    next_plugins["allow"] = [*allow, plugin_id]
    next_cfg["plugins"] = next_plugins
    return next_cfg


def enable_plugin_in_config(cfg: TConfig, plugin_id: str) -> dict[str, Any]:
    """Enable a provider plugin while honoring plugin allow/deny policy."""
    plugins = cfg.get("plugins")
    if isinstance(plugins, dict) and plugins.get("enabled") is False:
        return {"config": cfg, "enabled": False, "reason": "plugins disabled"}

    deny = plugins.get("deny") if isinstance(plugins, dict) else None
    if isinstance(deny, list) and plugin_id in deny:
        return {"config": cfg, "enabled": False, "reason": "blocked by denylist"}

    next_cfg = deepcopy(cfg)
    next_plugins = dict(next_cfg.get("plugins") or {})
    next_entries = dict(next_plugins.get("entries") or {})
    plugin_entry = dict(next_entries.get(plugin_id) or {})
    plugin_entry["enabled"] = True
    next_entries[plugin_id] = plugin_entry
    next_plugins["entries"] = next_entries
    next_cfg["plugins"] = next_plugins
    next_cfg = _ensure_plugin_allowlisted(next_cfg, plugin_id)
    return {"config": next_cfg, "enabled": True}
