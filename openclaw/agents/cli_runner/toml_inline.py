"""Minimal TOML inline serializer for CLI config overrides."""

from __future__ import annotations

import re
from typing import Any

_TOML_KEY_RE = re.compile(r"^[A-Za-z0-9_-]+$")


def _escape_toml_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _format_toml_key(key: str) -> str:
    return key if _TOML_KEY_RE.match(key) else f'"{_escape_toml_string(key)}"'


def serialize_toml_inline_value(value: Any) -> str:
    if isinstance(value, str):
        return f'"{_escape_toml_string(value)}"'
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float) and value == value:
        return str(value)
    if isinstance(value, list):
        return "[" + ", ".join(serialize_toml_inline_value(entry) for entry in value) + "]"
    if isinstance(value, dict):
        parts = [
            f"{_format_toml_key(str(k))} = {serialize_toml_inline_value(v)}"
            for k, v in value.items()
        ]
        return "{ " + ", ".join(parts) + " }"
    raise ValueError(f"Unsupported TOML inline value: {value!r}")


def format_toml_config_override(key: str, value: Any) -> str:
    return f"{key}={serialize_toml_inline_value(value)}"