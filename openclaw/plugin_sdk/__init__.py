"""Plugin SDK public API.

Mirrors src/plugin-sdk/. Most modules are barrel re-exports from other packages.
This provides self-contained param reader utilities, type stubs, and manifest constants.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

PLUGIN_MANIFEST_FILENAME = "openclaw.plugin.json"


def plugin_manifest_path(root: str) -> str:
    """Return the plugin manifest path for a given root directory."""
    return str(Path(root) / PLUGIN_MANIFEST_FILENAME)


def read_string_param(params: Mapping[str, Any], key: str, default: str | None = None) -> str | None:
    """Read a string parameter, returning default for missing/non-string values."""
    value = params.get(key)
    if isinstance(value, str):
        return value
    return default


def read_number_param(params: Mapping[str, Any], key: str, default: float | None = None) -> float | None:
    """Read a number parameter, returning default for missing/non-numeric values."""
    value = params.get(key)
    if isinstance(value, bool):
        return default
    if isinstance(value, (int, float)):
        return float(value)
    return default


def read_finite_number_param(params: Mapping[str, Any], key: str, default: float | None = None) -> float | None:
    """Read a finite number parameter, rejecting NaN/inf."""
    import math
    value = read_number_param(params, key, default)
    if value is None:
        return default
    if math.isnan(value) or math.isinf(value):
        return default
    return value


def read_positive_integer_param(params: Mapping[str, Any], key: str, default: int | None = None) -> int | None:
    """Read a positive integer parameter."""
    value = params.get(key)
    if isinstance(value, bool):
        return default
    if isinstance(value, int) and value > 0:
        return value
    if isinstance(value, float) and value > 0 and value == int(value):
        return int(value)
    return default


def read_non_negative_integer_param(params: Mapping[str, Any], key: str, default: int | None = None) -> int | None:
    """Read a non-negative integer parameter."""
    value = params.get(key)
    if isinstance(value, bool):
        return default
    if isinstance(value, int) and value >= 0:
        return value
    if isinstance(value, float) and value >= 0 and value == int(value):
        return int(value)
    return default


def read_string_array_param(params: Mapping[str, Any], key: str, default: list[str] | None = None) -> list[str] | None:
    """Read a string array parameter."""
    value = params.get(key)
    if isinstance(value, list):
        return [item for item in value if isinstance(item, str)]
    return default


def read_string_or_number_param(params: Mapping[str, Any], key: str, default: str | float | None = None) -> str | float | None:
    """Read a string or number parameter."""
    value = params.get(key)
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value
    return default
