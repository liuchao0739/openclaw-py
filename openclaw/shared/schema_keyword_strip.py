"""Recursively remove schema keywords unsupported by target provider/tool surface."""

from __future__ import annotations

from typing import Any, Iterable


def strip_unsupported_schema_keywords(
    schema: Any,
    unsupported_keywords: Iterable[str],
) -> Any:
    if not isinstance(schema, (dict, list)):
        return schema
    if isinstance(schema, list):
        return [strip_unsupported_schema_keywords(entry, unsupported_keywords) for entry in schema]
    cleaned: dict[str, Any] = {}
    for key, value in schema.items():
        if key in unsupported_keywords:
            continue
        if key == "properties" and isinstance(value, dict):
            cleaned[key] = {
                child_key: strip_unsupported_schema_keywords(child_value, unsupported_keywords)
                for child_key, child_value in value.items()
            }
            continue
        if key == "items" and isinstance(value, dict):
            if isinstance(value, list):
                cleaned[key] = [strip_unsupported_schema_keywords(entry, unsupported_keywords) for entry in value]
            else:
                cleaned[key] = strip_unsupported_schema_keywords(value, unsupported_keywords)
            continue
        if key in ("anyOf", "oneOf", "allOf") and isinstance(value, list):
            cleaned[key] = [strip_unsupported_schema_keywords(entry, unsupported_keywords) for entry in value]
            continue
        cleaned[key] = value
    return cleaned
