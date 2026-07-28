from __future__ import annotations

from typing import Any

from ._normalization import normalize_optional_string


def normalize_text(value: Any) -> str | None:
    return normalize_optional_string(value)