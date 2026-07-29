import copy
from typing import Any, Optional, TypedDict


class ConfigMigrationResult(TypedDict):
    config: Any
    changes: list


def _as_optional_record(value: Any) -> Optional[dict]:
    if isinstance(value, dict):
        return value
    return None


def _merge_host_config(legacy_host: dict, existing_host: Optional[dict]) -> dict:
    merged = dict(legacy_host)
    if existing_host:
        merged.update(existing_host)
    return merged


def migrate_legacy_canvas_host_config(config: Any) -> Optional[ConfigMigrationResult]:
    if not isinstance(config, dict):
        return None
    legacy_host = _as_optional_record(config.get("canvasHost"))
    if not legacy_host:
        return None

    plugins = copy.deepcopy(_as_optional_record(config.get("plugins")) or {})
    entries = _as_optional_record(plugins.get("entries")) or {}
    canvas_entry = _as_optional_record(entries.get("canvas")) or {}
    canvas_config = _as_optional_record(canvas_entry.get("config")) or {}
    existing_host = _as_optional_record(canvas_config.get("host"))

    entries["canvas"] = {
        **canvas_entry,
        "config": {
            **canvas_config,
            "host": _merge_host_config(legacy_host, existing_host),
        },
    }
    plugins["entries"] = entries

    next_config = {**config, "plugins": plugins}
    next_config.pop("canvasHost", None)

    return {
        "config": next_config,
        "changes": ["migrated canvasHost to plugins.entries.canvas.config.host"],
    }
