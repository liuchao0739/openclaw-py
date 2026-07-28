"""Frontmatter helpers parse Markdown frontmatter blocks and body text."""

from __future__ import annotations

import json
from typing import Any


def _normalize_csv_or_loose_string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        parts = [p.strip() for p in value.split(",")]
        return [p for p in parts if p]
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    return []


def normalize_string_list(input_value: Any) -> list[str]:
    return _normalize_csv_or_loose_string_list(input_value)


def get_frontmatter_string(frontmatter: dict[str, Any], key: str) -> str | None:
    value = frontmatter.get(key)
    return value if isinstance(value, str) else None


def parse_frontmatter_bool(value: str | None, fallback: bool) -> bool:
    if value is None:
        return fallback
    parsed = value.strip().lower()
    if parsed in ("true", "1", "yes"):
        return True
    if parsed in ("false", "0", "no"):
        return False
    return fallback


def resolve_openclaw_manifest_block(
    frontmatter: dict[str, Any],
    key: str = "metadata",
) -> dict[str, Any] | None:
    raw = get_frontmatter_string(frontmatter, key)
    if not raw:
        return None
    try:
        parsed = json.loads(raw)
        if not isinstance(parsed, dict):
            return None
        manifest_keys = ["metadata"]
        for k in manifest_keys:
            candidate = parsed.get(k)
            if candidate and isinstance(candidate, dict):
                return candidate
        return None
    except (json.JSONDecodeError, TypeError):
        return None


def resolve_openclaw_manifest_requires(
    metadata_obj: dict[str, Any],
) -> dict[str, list[str]] | None:
    requires_raw = metadata_obj.get("requires")
    if not isinstance(requires_raw, dict):
        return None
    return {
        "bins": normalize_string_list(requires_raw.get("bins")),
        "anyBins": normalize_string_list(requires_raw.get("anyBins")),
        "env": normalize_string_list(requires_raw.get("env")),
        "config": normalize_string_list(requires_raw.get("config")),
    }


def resolve_openclaw_manifest_install(
    metadata_obj: dict[str, Any],
    parse_install_spec: Any,
) -> list[Any]:
    install_raw = metadata_obj.get("install")
    if not isinstance(install_raw, list):
        return []
    result = []
    for entry in install_raw:
        parsed = parse_install_spec(entry)
        if parsed is not None:
            result.append(parsed)
    return result


def resolve_openclaw_manifest_os(metadata_obj: dict[str, Any]) -> list[str]:
    return normalize_string_list(metadata_obj.get("os"))


def parse_openclaw_manifest_install_base(
    input_value: Any,
    allowed_kinds: list[str],
) -> dict[str, Any] | None:
    if not isinstance(input_value, dict):
        return None
    raw = input_value
    kind_raw = raw.get("kind") or raw.get("type", "")
    if isinstance(kind_raw, str):
        kind = kind_raw.strip().lower()
    else:
        kind = ""
    if kind not in allowed_kinds:
        return None
    spec: dict[str, Any] = {"raw": raw, "kind": kind}
    if isinstance(raw.get("id"), str):
        spec["id"] = raw["id"]
    if isinstance(raw.get("label"), str):
        spec["label"] = raw["label"]
    bins = normalize_string_list(raw.get("bins"))
    if bins:
        spec["bins"] = bins
    return spec


def apply_openclaw_manifest_install_common_fields(
    spec: dict[str, Any],
    parsed: dict[str, Any],
) -> dict[str, Any]:
    for field in ("id", "label", "bins"):
        if field in parsed and parsed[field] is not None:
            spec[field] = parsed[field]
    return spec
