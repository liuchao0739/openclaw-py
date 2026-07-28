from __future__ import annotations

import json
import os
from typing import Any


def resolve_install_records_path() -> str:
    return os.path.join(".openclaw", "plugins", "install-records.json")


def load_install_records() -> dict[str, Any]:
    path = resolve_install_records_path()
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return {}


def save_install_records(records: dict[str, Any]) -> None:
    path = resolve_install_records_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(records, f, indent=2)


def record_install(
    plugin_id: str,
    version: str,
    source: str,
    records: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if records is None:
        records = load_install_records()
    records[plugin_id] = {
        "version": version,
        "source": source,
        "installedAt": __import__("time").time(),
    }
    save_install_records(records)
    return records


def get_install_record(
    plugin_id: str,
    records: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    if records is None:
        records = load_install_records()
    return records.get(plugin_id)
