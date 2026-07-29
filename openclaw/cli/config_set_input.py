from __future__ import annotations

from typing import Any

from openclaw.packages.normalization_core import normalize_optional_string


def normalize_config_set_value(raw: Any) -> str | None:
    if isinstance(raw, bool):
        return "true" if raw else "false"
    if isinstance(raw, (int, float)):
        return str(raw)
    return normalize_optional_string(raw)


def parse_config_set_input(key: str, value: Any) -> tuple[str, str | None]:
    return key, normalize_config_set_value(value)
