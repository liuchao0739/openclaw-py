"""Active Memory extension package."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


_MANIFEST_PATH = Path(__file__).resolve().parent / "openclaw_plugin.json"


def _load_manifest_config_schema() -> dict[str, Any]:
    manifest = json.loads(_MANIFEST_PATH.read_text(encoding="utf-8"))
    schema = manifest.get("configSchema")
    if not isinstance(schema, dict):
        raise ValueError("active-memory plugin manifest is missing configSchema")
    return schema


def _safe_parse(value: Any) -> dict[str, Any]:
    if value is None:
        return {"success": True, "data": None}
    if not isinstance(value, dict):
        return {
            "success": False,
            "error": {"issues": [{"path": [], "message": "expected config object"}]},
        }
    return {"success": True, "data": value}


active_memory_plugin_config_schema: dict[str, Any] = {
    "safeParse": _safe_parse,
    "jsonSchema": _load_manifest_config_schema(),
}


def register_active_memory_plugin_entry(api: Any) -> None:
    from openclaw_extensions.active_memory.plugin import register_active_memory_plugin
    register_active_memory_plugin(api)