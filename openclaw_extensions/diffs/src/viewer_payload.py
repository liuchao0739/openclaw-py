from __future__ import annotations

import json
from typing import Any

from .types import DIFF_INDICATORS, DIFF_LAYOUTS, DIFF_THEMES

OVERFLOW_VALUES = ("scroll", "wrap")


def _is_record(value: Any) -> bool:
    return value is not None and isinstance(value, dict)


def parse_viewer_payload_json(raw: str) -> dict[str, Any]:
    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        raise ValueError("Diff payload is not valid JSON.")
    if not _is_diff_viewer_payload(parsed):
        raise ValueError("Diff payload has invalid shape.")
    return parsed


def _is_diff_viewer_payload(value: Any) -> bool:
    if not _is_record(value):
        return False
    if not isinstance(value.get("prerenderedHTML"), str):
        return False
    langs = value.get("langs")
    if not isinstance(langs, list) or not all(isinstance(lang, str) for lang in langs):
        return False
    if not _is_viewer_options(value.get("options")):
        return False
    has_file_diff = _is_record(value.get("fileDiff"))
    has_before_after_files = _is_record(value.get("oldFile")) and _is_record(value.get("newFile"))
    if not has_file_diff and not has_before_after_files:
        return False
    return True


def _is_viewer_options(value: Any) -> bool:
    if not _is_record(value):
        return False
    theme = value.get("theme")
    if not _is_record(theme):
        return False
    if theme.get("light") != "pierre-light" or theme.get("dark") != "pierre-dark":
        return False
    if not _includes_value(DIFF_LAYOUTS, value.get("diffStyle")):
        return False
    if not _includes_value(DIFF_INDICATORS, value.get("diffIndicators")):
        return False
    if not _includes_value(DIFF_THEMES, value.get("themeType")):
        return False
    if not _includes_value(OVERFLOW_VALUES, value.get("overflow")):
        return False
    if not isinstance(value.get("disableLineNumbers"), bool):
        return False
    if not isinstance(value.get("expandUnchanged"), bool):
        return False
    if not isinstance(value.get("backgroundEnabled"), bool):
        return False
    if not isinstance(value.get("unsafeCSS"), str):
        return False
    return True


def _includes_value(values: tuple[str, ...], value: Any) -> bool:
    return isinstance(value, str) and value in values