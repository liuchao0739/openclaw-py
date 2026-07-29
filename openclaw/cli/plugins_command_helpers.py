from __future__ import annotations

from typing import Any

from openclaw.packages.normalization_core import normalize_optional_string


def resolve_plugin_name(raw: str | None) -> str | None:
    return normalize_optional_string(raw)


def format_plugin_label(name: str, version: str | None = None) -> str:
    return f"{name}@{version}" if version else name
