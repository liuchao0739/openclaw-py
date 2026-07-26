"""Diffs helper module supports config behavior."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from openclaw.packages.normalization_core import is_record

_MANIFEST_PATH = Path(__file__).resolve().parents[1] / "openclaw.plugin.json"


def _load_manifest_config_schema() -> dict[str, Any]:
    manifest = json.loads(_MANIFEST_PATH.read_text(encoding="utf-8"))
    schema = manifest.get("configSchema")
    if not is_record(schema):
        raise ValueError("diffs plugin manifest is missing configSchema")
    return schema


def _safe_parse(value: Any) -> dict[str, Any]:
    if value is None:
        return {"success": True, "data": None}
    if not is_record(value):
        return {
            "success": False,
            "error": {"issues": [{"path": [], "message": "expected config object"}]},
        }
    return {"success": True, "data": value}


DEFAULT_DIFFS_TOOL_DEFAULTS: dict[str, Any] = {
    "fontFamily": "Fira Code",
    "fontSize": 15,
    "lineSpacing": 1.6,
    "layout": "unified",
    "showLineNumbers": True,
    "diffIndicators": "bars",
    "wordWrap": True,
    "background": True,
    "theme": "dark",
    "fileFormat": "png",
    "fileQuality": "standard",
    "fileScale": 2,
    "fileMaxWidth": 960,
    "mode": "both",
    "ttlSeconds": 1800,
}

DEFAULT_DIFFS_PLUGIN_SECURITY: dict[str, bool] = {
    "allowRemoteViewer": False,
}


def resolve_diffs_plugin_defaults(config: object) -> dict[str, Any]:
    if not is_record(config):
        return dict(DEFAULT_DIFFS_TOOL_DEFAULTS)
    defaults = config.get("defaults")
    if not is_record(defaults):
        return dict(DEFAULT_DIFFS_TOOL_DEFAULTS)
    merged = dict(DEFAULT_DIFFS_TOOL_DEFAULTS)
    merged.update(defaults)
    return merged


def resolve_diffs_plugin_security(config: object) -> dict[str, bool]:
    if not is_record(config):
        return dict(DEFAULT_DIFFS_PLUGIN_SECURITY)
    security = config.get("security")
    if not is_record(security):
        return dict(DEFAULT_DIFFS_PLUGIN_SECURITY)
    return {
        "allowRemoteViewer": security.get("allowRemoteViewer") is True,
    }


def resolve_diffs_plugin_viewer_base_url(config: object) -> str | None:
    if not is_record(config):
        return None
    viewer_base_url = config.get("viewerBaseUrl")
    if not isinstance(viewer_base_url, str):
        return None
    normalized = viewer_base_url.strip()
    return normalized or None


diffs_plugin_config_schema: dict[str, Any] = {
    "safeParse": _safe_parse,
    "jsonSchema": _load_manifest_config_schema(),
}
