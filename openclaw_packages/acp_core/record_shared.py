from __future__ import annotations

from typing import Any

from ._normalization import as_optional_record


def as_record(value: Any) -> dict[str, Any] | None:
    return as_optional_record(value)