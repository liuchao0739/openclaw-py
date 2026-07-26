"""Brave plugin config schema."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from openclaw.packages.normalization_core import is_record

_MANIFEST_PATH = Path(__file__).resolve().parents[1] / "openclaw.plugin.json"
_ALLOWED_MODES = {"web", "llm-context"}


def _load_manifest_config_schema() -> dict[str, Any]:
    manifest = json.loads(_MANIFEST_PATH.read_text(encoding="utf-8"))
    schema = manifest.get("configSchema")
    if not is_record(schema):
        raise ValueError("brave plugin manifest is missing configSchema")
    return schema


def _validate_web_search_config(value: Any) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    if not is_record(value):
        return issues
    web_search = value.get("webSearch")
    if web_search is None:
        return issues
    if not is_record(web_search):
        issues.append({"path": ["webSearch"], "message": "expected object"})
        return issues
    mode = web_search.get("mode")
    if mode is not None and mode not in _ALLOWED_MODES:
        issues.append(
            {
                "path": ["webSearch", "mode"],
                "message": (
                    'must be equal to one of the allowed values (allowed: "web", "llm-context")'
                ),
            }
        )
    return issues


def _safe_parse(value: Any) -> dict[str, Any]:
    if value is None:
        return {"success": True, "data": None}
    if not is_record(value):
        return {
            "success": False,
            "error": {"issues": [{"path": [], "message": "expected config object"}]},
        }
    issues = _validate_web_search_config(value)
    if issues:
        return {"success": False, "error": {"issues": issues}}
    return {"success": True, "data": value}


brave_plugin_config_schema: dict[str, Any] = {
    "safeParse": _safe_parse,
    "jsonSchema": _load_manifest_config_schema(),
}
