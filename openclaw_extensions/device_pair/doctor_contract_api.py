import os
import json
import shutil
from typing import Dict, List

from .notify_state import (
    DEVICE_PAIR_NOTIFY_LEGACY_STATE_FILE,
    DEVICE_PAIR_NOTIFY_SUBSCRIBER_MAX_ENTRIES,
    DEVICE_PAIR_NOTIFY_SUBSCRIBER_NAMESPACE,
    NotifySubscription,
    notify_subscriber_store_key,
    normalize_legacy_notify_state,
)


def _resolve_legacy_notify_state_path(state_dir: str) -> str:
    return os.path.join(state_dir, DEVICE_PAIR_NOTIFY_LEGACY_STATE_FILE)


def _file_exists(file_path: str) -> bool:
    try:
        return os.path.isfile(file_path)
    except Exception:
        return False


def _read_legacy_notify_state(file_path: str) -> Dict:
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return normalize_legacy_notify_state(json.load(f))
    except Exception:
        return {"subscribers": [], "notifiedRequestIds": {}}


def _archive_legacy_source(params: Dict) -> None:
    file_path = params["filePath"]
    changes = params["changes"]
    warnings = params["warnings"]

    archived_path = f"{file_path}.migrated"
    if _file_exists(archived_path):
        warnings.append(
            f"Left migrated Device Pair notify-state source in place because {archived_path} already exists"
        )
        return
    try:
        shutil.move(file_path, archived_path)
        changes.append(f"Archived Device Pair notify-state legacy source -> {archived_path}")
    except Exception as err:
        warnings.append(f"Failed archiving Device Pair notify-state legacy source: {str(err)}")


def _migrate_device_pair_notify_json_to_plugin_state(params: Dict) -> Dict:
    changes: List[str] = []
    warnings: List[str] = []
    file_path = _resolve_legacy_notify_state_path(params["stateDir"])
    state = _read_legacy_notify_state(file_path)
    if not state or not state.get("subscribers"):
        return {"changes": changes, "warnings": warnings}

    context = params["context"]
    store = context.openPluginStateKeyedStore({
        "namespace": DEVICE_PAIR_NOTIFY_SUBSCRIBER_NAMESPACE,
        "maxEntries": DEVICE_PAIR_NOTIFY_SUBSCRIBER_MAX_ENTRIES,
    })
    imported = 0
    already_present = 0
    for subscriber in state["subscribers"]:
        key = notify_subscriber_store_key(subscriber)
        inserted = store.registerIfAbsent(key, subscriber)
        if inserted:
            imported += 1
        else:
            already_present += 1

    changes.append(
        f"Migrated Device Pair notify subscribers -> plugin state ({imported} imported, {already_present} already present)"
    )
    _archive_legacy_source({"filePath": file_path, "changes": changes, "warnings": warnings})
    return {"changes": changes, "warnings": warnings}


def _detect_device_pair_notify_json_to_plugin_state(params: Dict) -> Dict:
    file_path = _resolve_legacy_notify_state_path(params["stateDir"])
    state = _read_legacy_notify_state(file_path)
    if not state or not state.get("subscribers"):
        return None
    return {
        "preview": [
            f"- Device Pair notify subscribers: {file_path} -> plugin state ({DEVICE_PAIR_NOTIFY_SUBSCRIBER_NAMESPACE}, {len(state['subscribers'])} subscriber(s))"
        ]
    }


state_migrations = [
    {
        "id": "device-pair-notify-json-to-plugin-state",
        "label": "Device Pair notify subscribers",
        "detectLegacyState": _detect_device_pair_notify_json_to_plugin_state,
        "migrateLegacyState": _migrate_device_pair_notify_json_to_plugin_state,
    },
]

__all__ = ["state_migrations"]
