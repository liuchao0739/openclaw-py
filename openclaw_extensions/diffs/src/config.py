from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from openclaw.packages.normalization_core import is_record

_MANIFEST_PATH = Path(__file__).resolve().parents[1] / "openclaw.plugin.json"

DIFF_LAYOUTS: tuple[str, ...] = ("unified", "split")
DIFF_MODES: tuple[str, ...] = ("view", "image", "file", "both")
DIFF_THEMES: tuple[str, ...] = ("light", "dark")
DIFF_INDICATORS: tuple[str, ...] = ("bars", "classic", "none")
DIFF_IMAGE_QUALITY_PRESETS: tuple[str, ...] = ("standard", "hq", "print")
DIFF_OUTPUT_FORMATS: tuple[str, ...] = ("png", "pdf")

DEFAULT_IMAGE_QUALITY_PROFILES: dict[str, dict[str, int]] = {
    "standard": {"scale": 2, "maxWidth": 960, "maxPixels": 8_000_000},
    "hq": {"scale": 2.5, "maxWidth": 1200, "maxPixels": 14_000_000},
    "print": {"scale": 3, "maxWidth": 1400, "maxPixels": 24_000_000},
}

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
    return {"success": True, "data": _build_diffs_plugin_config_shape(value)}


def _resolve_configured_value(params: dict[str, Any]) -> Any:
    primary = params.get("primary")
    aliases = params.get("aliases", [])
    schema_default = params.get("schemaDefault")
    if primary != schema_default:
        return primary
    for alias in aliases:
        if alias is not None:
            return alias
    return primary


def _build_diffs_plugin_config_shape(config: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    viewer_base_url = resolve_diffs_plugin_viewer_base_url(config)
    if viewer_base_url is not None:
        result["viewerBaseUrl"] = viewer_base_url
    defaults = config.get("defaults")
    if defaults and isinstance(defaults, dict):
        result["defaults"] = resolve_diffs_plugin_defaults(config)
    security = config.get("security")
    if security and isinstance(security, dict):
        result["security"] = resolve_diffs_plugin_security(config)
    return result


def resolve_diffs_plugin_defaults(config: object) -> dict[str, Any]:
    if not is_record(config):
        return dict(DEFAULT_DIFFS_TOOL_DEFAULTS)
    defaults = config.get("defaults")
    if not is_record(defaults):
        return dict(DEFAULT_DIFFS_TOOL_DEFAULTS)

    file_quality = _normalize_file_quality(
        _resolve_configured_value({
            "primary": defaults.get("fileQuality"),
            "aliases": [defaults.get("imageQuality")],
            "schemaDefault": DEFAULT_DIFFS_TOOL_DEFAULTS["fileQuality"],
        })
    )
    profile = DEFAULT_IMAGE_QUALITY_PROFILES.get(file_quality, DEFAULT_IMAGE_QUALITY_PROFILES["standard"])
    file_format = _normalize_file_format(
        _resolve_configured_value({
            "primary": defaults.get("fileFormat"),
            "aliases": [defaults.get("imageFormat"), defaults.get("format")],
            "schemaDefault": DEFAULT_DIFFS_TOOL_DEFAULTS["fileFormat"],
        })
    )
    file_scale = _normalize_file_scale(
        _resolve_configured_value({
            "primary": defaults.get("fileScale"),
            "aliases": [defaults.get("imageScale")],
        }),
        profile["scale"],
    )
    file_max_width = _normalize_file_max_width(
        _resolve_configured_value({
            "primary": defaults.get("fileMaxWidth"),
            "aliases": [defaults.get("imageMaxWidth")],
        }),
        profile["maxWidth"],
    )

    return {
        "fontFamily": _normalize_font_family(defaults.get("fontFamily")),
        "fontSize": normalize_diff_font_size(defaults.get("fontSize")),
        "lineSpacing": normalize_diff_line_spacing(defaults.get("lineSpacing")),
        "layout": _normalize_layout(defaults.get("layout")),
        "showLineNumbers": defaults.get("showLineNumbers", True) is not False,
        "diffIndicators": _normalize_diff_indicators(defaults.get("diffIndicators")),
        "wordWrap": defaults.get("wordWrap", True) is not False,
        "background": defaults.get("background", True) is not False,
        "theme": _normalize_theme(defaults.get("theme")),
        "fileFormat": _normalize_file_format(file_format),
        "fileQuality": file_quality,
        "fileScale": file_scale,
        "fileMaxWidth": file_max_width,
        "mode": _normalize_mode(defaults.get("mode")),
        "ttlSeconds": _normalize_ttl_seconds(defaults.get("ttlSeconds")),
    }


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


def _normalize_font_family(font_family: str | None) -> str:
    normalized = font_family.strip() if font_family else None
    return normalized or DEFAULT_DIFFS_TOOL_DEFAULTS["fontFamily"]


def normalize_diff_font_size(font_size: int | None) -> int:
    if font_size is None or not isinstance(font_size, (int, float)) or not math.isfinite(font_size):
        return DEFAULT_DIFFS_TOOL_DEFAULTS["fontSize"]
    rounded = math.floor(font_size)
    return min(max(rounded, 10), 24)


def normalize_diff_line_spacing(line_spacing: float | None) -> float:
    if line_spacing is None or not isinstance(line_spacing, (int, float)) or not math.isfinite(line_spacing):
        return DEFAULT_DIFFS_TOOL_DEFAULTS["lineSpacing"]
    return float(min(max(line_spacing, 1), 3))


def _normalize_layout(layout: str | None) -> str:
    if layout and layout in DIFF_LAYOUTS:
        return layout
    return DEFAULT_DIFFS_TOOL_DEFAULTS["layout"]


def _normalize_diff_indicators(diff_indicators: str | None) -> str:
    if diff_indicators and diff_indicators in DIFF_INDICATORS:
        return diff_indicators
    return DEFAULT_DIFFS_TOOL_DEFAULTS["diffIndicators"]


def _normalize_theme(theme: str | None) -> str:
    if theme and theme in DIFF_THEMES:
        return theme
    return DEFAULT_DIFFS_TOOL_DEFAULTS["theme"]


def _normalize_file_format(file_format: str | None) -> str:
    if file_format and file_format in DIFF_OUTPUT_FORMATS:
        return file_format
    return DEFAULT_DIFFS_TOOL_DEFAULTS["fileFormat"]


def _normalize_file_quality(file_quality: str | None) -> str:
    if file_quality and file_quality in DIFF_IMAGE_QUALITY_PRESETS:
        return file_quality
    return DEFAULT_DIFFS_TOOL_DEFAULTS["fileQuality"]


def _normalize_file_scale(file_scale: float | None, fallback: float) -> float:
    if file_scale is None or not isinstance(file_scale, (int, float)) or not math.isfinite(file_scale):
        return fallback
    rounded = round(file_scale * 100) / 100
    return float(min(max(rounded, 1), 4))


def _normalize_file_max_width(file_max_width: int | None, fallback: int) -> int:
    if file_max_width is None or not isinstance(file_max_width, (int, float)) or not math.isfinite(file_max_width):
        return fallback
    rounded = round(file_max_width)
    return min(max(rounded, 640), 2400)


def _normalize_mode(mode: str | None) -> str:
    if mode and mode in DIFF_MODES:
        return mode
    return DEFAULT_DIFFS_TOOL_DEFAULTS["mode"]


def _normalize_ttl_seconds(ttl_seconds: int | None) -> int:
    if ttl_seconds is None or not isinstance(ttl_seconds, (int, float)) or not math.isfinite(ttl_seconds):
        return DEFAULT_DIFFS_TOOL_DEFAULTS["ttlSeconds"]
    rounded = math.floor(ttl_seconds)
    return min(max(rounded, 1), 21600)


def resolve_diff_image_render_options(params: dict[str, Any]) -> dict[str, Any]:
    defaults = params.get("defaults", DEFAULT_DIFFS_TOOL_DEFAULTS)
    fmt = _normalize_file_format(
        params.get("fileFormat")
        or params.get("imageFormat")
        or params.get("format")
        or defaults.get("fileFormat", "png")
    )
    quality_override_provided = (
        params.get("fileQuality") is not None or params.get("imageQuality") is not None
    )
    quality_preset = _normalize_file_quality(
        params.get("fileQuality") or params.get("imageQuality") or defaults.get("fileQuality", "standard")
    )
    profile = DEFAULT_IMAGE_QUALITY_PROFILES.get(quality_preset, DEFAULT_IMAGE_QUALITY_PROFILES["standard"])
    scale = _normalize_file_scale(
        params.get("fileScale") or params.get("imageScale"),
        profile["scale"] if quality_override_provided else defaults.get("fileScale", profile["scale"]),
    )
    max_width = _normalize_file_max_width(
        params.get("fileMaxWidth") or params.get("imageMaxWidth"),
        profile["maxWidth"] if quality_override_provided else defaults.get("fileMaxWidth", profile["maxWidth"]),
    )
    return {
        "format": fmt,
        "qualityPreset": quality_preset,
        "scale": scale,
        "maxWidth": max_width,
        "maxPixels": profile["maxPixels"],
    }


diffs_plugin_config_schema: dict[str, Any] = {
    "safeParse": _safe_parse,
    "jsonSchema": _load_manifest_config_schema(),
}