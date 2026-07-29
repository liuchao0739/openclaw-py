from __future__ import annotations

from typing import Any

from openclaw.packages.normalization_core import normalize_optional_string


def normalize_container_target(value: Any) -> str | None:
    return normalize_optional_string(value)


def is_valid_container_target(target: str | None) -> bool:
    return bool(target and len(target) > 0)
