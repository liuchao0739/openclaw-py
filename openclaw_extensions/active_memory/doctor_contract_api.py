from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any


TOGGLE_STATE_FILE = "session-toggles.json"
SESSION_TOGGLES_NAMESPACE = "session-toggles"
MAX_TOGGLE_ENTRIES = 10_000


def _resolve_toggle_state_path(state_dir: str) -> Path:
    return Path(state_dir) / "plugins" / "active-memory" / TOGGLE_STATE_FILE


def _active_memory_toggle_key(session_key: str) -> str:
    return hashlib.sha256(session_key.encode("utf-8")).hexdigest()


async def _file_exists(file_path: Path) -> bool:
    try:
        return file_path.is_file()
    except OSError:
        return False


async def _read_legacy_toggle_entries(file_path: Path) -> list[dict[str, Any]]:
    try:
        raw = file_path.read_text(encoding="utf-8")
        parsed = json.loads(raw)
        if not isinstance(parsed, dict):
            return []
        sessions = parsed.get("sessions")
        if not isinstance(sessions, dict):
            return []
        entries: list[dict[str, Any]] = []
        for session_key, value in sessions.items():
            if not isinstance(session_key, str) or not session_key.strip():
                continue
            if not isinstance(value, dict):
                continue
            if value.get("disabled") is not True:
                continue
            updated_at = value.get("updatedAt")
            if not isinstance(updated_at, (int, float)):
                import time
                updated_at = int(time.time() * 1000)
            entries.append({
                "sessionKey": session_key,
                "disabled": True,
                "updatedAt": int(updated_at),
            })
        return entries
    except (OSError, json.JSONDecodeError, ValueError):
        return []


async def _archive_legacy_source(
    file_path: Path,
    label: str,
    changes: list[str],
    warnings: list[str],
) -> None:
    archived_path = file_path.with_suffix(".migrated")
    if await _file_exists(archived_path):
        warnings.append(
            f"Left migrated {label} source in place because {archived_path} already exists"
        )
        return
    try:
        os.rename(file_path, archived_path)
        changes.append(f"Archived {label} legacy source -> {archived_path}")
    except OSError as err:
        warnings.append(f"Failed archiving {label} legacy source: {err}")


async def _detect_legacy_state(params: dict[str, Any]) -> dict[str, Any] | None:
    state_dir = params.get("stateDir", "")
    if not state_dir:
        return None
    file_path = _resolve_toggle_state_path(state_dir)
    entries = await _read_legacy_toggle_entries(file_path)
    if not entries:
        return None
    count = len(entries)
    entry_label = "entry" if count == 1 else "entries"
    return {
        "preview": [
            f"- Active Memory session toggles: {count} {entry_label} -> plugin state ({SESSION_TOGGLES_NAMESPACE})",
        ],
    }


async def _migrate_legacy_state(params: dict[str, Any]) -> dict[str, list[str]]:
    changes: list[str] = []
    warnings: list[str] = []
    state_dir = params.get("stateDir", "")
    if not state_dir:
        return {"changes": changes, "warnings": warnings}
    file_path = _resolve_toggle_state_path(state_dir)
    entries = await _read_legacy_toggle_entries(file_path)
    if not entries:
        return {"changes": changes, "warnings": warnings}

    context = params.get("context", {})
    open_plugin_state_keyed_store = context.get("openPluginStateKeyedStore")
    if open_plugin_state_keyed_store is None:
        return {"changes": changes, "warnings": warnings}

    store = open_plugin_state_keyed_store({
        "namespace": SESSION_TOGGLES_NAMESPACE,
        "maxEntries": MAX_TOGGLE_ENTRIES,
    })

    existing_keys: set[str] = set()
    try:
        store_entries = await store.entries()
        for entry in store_entries:
            key = entry.get("key") if isinstance(entry, dict) else None
            if key:
                existing_keys.add(key)
    except Exception:
        pass

    missing_entries = [
        entry for entry in entries
        if _active_memory_toggle_key(entry["sessionKey"]) not in existing_keys
    ]

    if len(missing_entries) > MAX_TOGGLE_ENTRIES - len(existing_keys):
        warnings.append(
            f"Skipped Active Memory session toggle migration because plugin state has room for "
            f"{MAX_TOGGLE_ENTRIES - len(existing_keys)} of {len(missing_entries)} missing entries; "
            f"left legacy source in place"
        )
        return {"changes": changes, "warnings": warnings}

    imported = 0
    for entry in entries:
        key = _active_memory_toggle_key(entry["sessionKey"])
        if key in existing_keys:
            continue
        try:
            await store.register(key, entry)
            existing_keys.add(key)
            imported += 1
        except Exception:
            pass

    if imported > 0:
        entry_label = "entry" if imported == 1 else "entries"
        changes.append(
            f"Migrated {imported} Active Memory session toggle {entry_label} -> plugin state"
        )

    await _archive_legacy_source(
        file_path=file_path,
        label="Active Memory session toggles",
        changes=changes,
        warnings=warnings,
    )
    return {"changes": changes, "warnings": warnings}


state_migrations: list[dict[str, Any]] = [
    {
        "id": "active-memory-session-toggles-json-to-plugin-state",
        "label": "Active Memory session toggles",
        "detect_legacy_state": _detect_legacy_state,
        "migrate_legacy_state": _migrate_legacy_state,
    },
]