from __future__ import annotations

import json
from typing import Any, TypeVar

T = TypeVar("T")

try:
    from pydantic import BaseModel, ValidationError

    _HAS_PYGANTIC = True
except ImportError:
    _HAS_PYGANTIC = False


def safe_parse_with_schema(schema: Any, value: Any) -> Any:
    if not _HAS_PYGANTIC:
        return value
    if isinstance(schema, type) and issubclass(schema, BaseModel):
        try:
            return schema.model_validate(value)
        except ValidationError:
            return None
    return value


def safe_parse_json_with_schema(schema: Any, raw: str) -> Any:
    try:
        parsed = json.loads(raw)
    except (ValueError, TypeError):
        return None
    return safe_parse_with_schema(schema, parsed)
