from __future__ import annotations

import copy
from typing import Any

from openclaw.packages.normalization_core import is_record

LEGACY_PATH = "models.bedrockDiscovery"
TARGET_PATH = "plugins.entries.amazon-bedrock.config.discovery"
_BLOCKED_OBJECT_KEYS = frozenset({"__proto__", "prototype", "constructor"})


def _is_blocked_object_key(key: str) -> bool:
    return key in _BLOCKED_OBJECT_KEYS


def _get_record(value: Any) -> dict[str, Any] | None:
    return value if is_record(value) else None


def _ensure_record(root: dict[str, Any], key: str) -> dict[str, Any]:
    existing = _get_record(root.get(key))
    if existing is not None:
        return existing
    next_record: dict[str, Any] = {}
    root[key] = next_record
    return next_record


def _merge_missing(target: dict[str, Any], source: dict[str, Any]) -> None:
    for key, value in source.items():
        if value is None or _is_blocked_object_key(key):
            continue
        existing = target.get(key)
        if existing is None:
            target[key] = value
            continue
        if is_record(existing) and is_record(value):
            _merge_missing(existing, value)


def _clone_record(value: dict[str, Any] | None) -> dict[str, Any]:
    return copy.copy(value) if value is not None else {}


def _resolve_legacy_bedrock_discovery_config(raw: Any) -> dict[str, Any] | None:
    if not is_record(raw):
        return None
    models = _get_record(raw.get("models"))
    if models is None:
        return None
    return _get_record(models.get("bedrockDiscovery"))


def _prune_empty_models_root(root: dict[str, Any]) -> None:
    models = _get_record(root.get("models"))
    if models is not None and len(models) == 0:
        del root["models"]


def migrate_amazon_bedrock_legacy_config(raw: Any) -> dict[str, Any]:
    if not is_record(raw):
        return {"config": raw, "changes": []}

    legacy = _resolve_legacy_bedrock_discovery_config(raw)
    if legacy is None:
        return {"config": raw, "changes": []}

    next_root = copy.deepcopy(raw)
    models = _ensure_record(next_root, "models")
    if "bedrockDiscovery" in models:
        del models["bedrockDiscovery"]
    _prune_empty_models_root(next_root)

    changes: list[str] = []
    if len(legacy) == 0:
        changes.append(f"Removed empty {LEGACY_PATH}.")
        return {"config": next_root, "changes": changes}

    plugins = _ensure_record(next_root, "plugins")
    entries = _ensure_record(plugins, "entries")
    entry = _ensure_record(entries, "amazon-bedrock")
    config = _ensure_record(entry, "config")
    existing = _get_record(config.get("discovery"))

    if existing is None:
        config["discovery"] = _clone_record(legacy)
        changes.append(f"Moved {LEGACY_PATH} → {TARGET_PATH}.")
        return {"config": next_root, "changes": changes}

    merged = _clone_record(existing)
    _merge_missing(merged, legacy)
    config["discovery"] = merged
    if str(sorted(merged.items())) != str(sorted(existing.items())):
        changes.append(
            f"Merged {LEGACY_PATH} → {TARGET_PATH} (filled missing fields from legacy; kept explicit plugin config values)."
        )
        return {"config": next_root, "changes": changes}

    changes.append(f"Removed {LEGACY_PATH} ({TARGET_PATH} already set).")
    return {"config": next_root, "changes": changes}