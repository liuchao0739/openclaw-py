import os
from typing import Any, Optional, TypedDict


class CanvasHostConfig(TypedDict, total=False):
    enabled: bool
    root: str
    port: int
    liveReload: bool


class CanvasPluginConfig(TypedDict, total=False):
    host: CanvasHostConfig


def _is_truthy_env_value(value: Optional[str]) -> bool:
    if not value:
        return False
    return value.strip().lower() in ("1", "true", "yes", "on")


def _is_record(value: Any) -> bool:
    return isinstance(value, dict)


def _as_boolean(value: Any) -> Optional[bool]:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in ("true", "1", "yes", "on"):
            return True
        if lowered in ("false", "0", "no", "off"):
            return False
    if isinstance(value, int):
        if value == 1:
            return True
        if value == 0:
            return False
    return None


def _read_string_value(value: Any) -> Optional[str]:
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float, bool)):
        return str(value)
    return None


def _read_positive_integer(value: Any) -> Optional[int]:
    if isinstance(value, int) and not isinstance(value, bool) and value > 0:
        return value
    if isinstance(value, str):
        try:
            parsed = int(value)
            if parsed > 0:
                return parsed
        except ValueError:
            pass
    return None


def _parse_canvas_host_config(value: Any) -> Optional[CanvasHostConfig]:
    if not _is_record(value):
        return None
    config: CanvasHostConfig = {}
    enabled = _as_boolean(value.get("enabled"))
    if enabled is not None:
        config["enabled"] = enabled
    root = _read_string_value(value.get("root"))
    if root is not None:
        config["root"] = root
    port = _read_positive_integer(value.get("port"))
    if port is not None:
        config["port"] = port
    live_reload = _as_boolean(value.get("liveReload"))
    if live_reload is not None:
        config["liveReload"] = live_reload
    return config if config else None


def parse_canvas_plugin_config(value: Any) -> CanvasPluginConfig:
    if not _is_record(value):
        return {}
    host = _parse_canvas_host_config(value.get("host"))
    return {"host": host} if host else {}


def _resolve_plugin_config_object(config: Any, plugin_id: str) -> dict:
    if not isinstance(config, dict):
        return {}
    plugins = config.get("plugins", {})
    if not isinstance(plugins, dict):
        return {}
    entries = plugins.get("entries", {})
    if not isinstance(entries, dict):
        return {}
    entry = entries.get(plugin_id, {})
    if not isinstance(entry, dict):
        return {}
    plugin_config = entry.get("config", {})
    return plugin_config if isinstance(plugin_config, dict) else {}


def _resolve_effective_enable_state(
    id: str, origin: str, config: Any, root_config: Any, enabled_by_default: bool
) -> dict:
    enabled = enabled_by_default
    if isinstance(config, dict):
        allow = config.get("allow")
        deny = config.get("deny")
        if isinstance(allow, list) and id not in allow:
            enabled = False
        if isinstance(deny, list) and id in deny:
            enabled = False
        entries = config.get("entries", {})
        if isinstance(entries, dict):
            entry = entries.get(id, {})
            if isinstance(entry, dict) and "enabled" in entry:
                enabled = bool(entry["enabled"])
    return {"enabled": enabled}


def _normalize_plugins_config(plugins: Any) -> Any:
    if isinstance(plugins, dict):
        return plugins
    return {}


def is_canvas_plugin_enabled(config: Any = None) -> bool:
    if config is None:
        return True
    return _resolve_effective_enable_state(
        id="canvas",
        origin="bundled",
        config=_normalize_plugins_config(config.get("plugins") if isinstance(config, dict) else {}),
        root_config=config,
        enabled_by_default=True,
    )["enabled"]


def resolve_canvas_host_config(
    config: Any = None, plugin_config: Optional[dict] = None
) -> CanvasHostConfig:
    resolved_plugin_config = plugin_config if plugin_config is not None else _resolve_plugin_config_object(config, "canvas")
    parsed = parse_canvas_plugin_config(resolved_plugin_config)
    return parsed.get("host", {})


def is_canvas_host_enabled(config: Any = None) -> bool:
    if _is_truthy_env_value(os.environ.get("OPENCLAW_SKIP_CANVAS_HOST")):
        return False
    if not is_canvas_plugin_enabled(config):
        return False
    return resolve_canvas_host_config(config).get("enabled") is not False


canvas_config_schema: dict = {
    "parse": parse_canvas_plugin_config,
    "uiHints": {
        "host": {
            "label": "Canvas Host",
            "help": "Serves local Canvas and A2UI files for paired nodes.",
            "advanced": True,
        },
        "host.enabled": {
            "label": "Canvas Host Enabled",
            "advanced": True,
        },
        "host.root": {
            "label": "Canvas Host Root Directory",
            "help": "Directory to serve. Defaults to the OpenClaw state canvas directory.",
            "advanced": True,
        },
        "host.port": {
            "label": "Canvas Host Port",
            "advanced": True,
        },
        "host.liveReload": {
            "label": "Canvas Host Live Reload",
            "advanced": True,
        },
    },
}
