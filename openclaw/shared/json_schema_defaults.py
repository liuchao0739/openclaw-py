"""JSON schema default helpers for TypeBox compiler normalization."""

from __future__ import annotations

import json
import re
from typing import Any


def _is_record(value: Any) -> bool:
    return isinstance(value, dict)


def _is_string_array(value: Any) -> bool:
    return isinstance(value, list) and all(isinstance(entry, str) for entry in value)


_SCHEMA_MAP_KEYWORDS = {
    "$defs", "definitions", "dependentSchemas", "patternProperties", "properties",
}
_SCHEMA_VALUE_KEYWORDS = {
    "additionalItems", "additionalProperties", "contains", "else", "if", "items",
    "not", "propertyNames", "then", "unevaluatedItems", "unevaluatedProperties",
}
_SCHEMA_ARRAY_KEYWORDS = {"allOf", "anyOf", "oneOf", "prefixItems"}
_SCHEMA_COMBINATOR_KEYWORDS = {"allOf", "anyOf", "oneOf"}
_JSON_SCHEMA_TYPES = {"array", "boolean", "integer", "null", "number", "object", "string"}


def _compiles_unicode_pattern(pattern: str) -> bool:
    try:
        re.compile(pattern)
        return True
    except re.error:
        return False


def repair_json_schema_pattern_for_unicode_reg_exp(pattern: str) -> str:
    if _compiles_unicode_pattern(pattern):
        return pattern
    repaired = re.sub(r"\\([^\\])", lambda m: m.group(1) if m.group(1) in (":", "/") else m.group(0), pattern)
    return repaired if _compiles_unicode_pattern(repaired) else pattern


def normalize_json_schema_for_type_box(schema: Any) -> Any:
    if not _is_record(schema):
        if isinstance(schema, list):
            return [normalize_json_schema_for_type_box(entry) for entry in schema]
        return schema
    result: dict[str, Any] = {}
    for key, value in schema.items():
        if key == "$dynamicRef" and "$ref" not in schema:
            result["$ref"] = value
        elif key == "pattern" and isinstance(value, str):
            result[key] = repair_json_schema_pattern_for_unicode_reg_exp(value)
        elif key == "patternProperties" and _is_record(value):
            result[key] = {
                repair_json_schema_pattern_for_unicode_reg_exp(k): normalize_json_schema_for_type_box(v)
                for k, v in value.items()
            }
        elif key in _SCHEMA_MAP_KEYWORDS and _is_record(value):
            result[key] = {k: normalize_json_schema_for_type_box(v) for k, v in value.items()}
        elif key == "dependencies" and _is_record(value):
            result[key] = {
                k: v if _is_string_array(v) else normalize_json_schema_for_type_box(v)
                for k, v in value.items()
            }
        elif key in _SCHEMA_VALUE_KEYWORDS or key in _SCHEMA_ARRAY_KEYWORDS:
            if isinstance(value, bool) or _is_record(value):
                result[key] = normalize_json_schema_for_type_box(value)
            elif isinstance(value, list):
                if key == "items":
                    result[key] = [normalize_json_schema_for_type_box(entry) for entry in value]
                else:
                    result[key] = [normalize_json_schema_for_type_box(entry) for entry in value]
            else:
                result[key] = value
        else:
            result[key] = value
    return result


def find_json_schema_shape_error(schema: Any) -> str | None:
    if not _is_record(schema):
        if isinstance(schema, bool):
            return None
        return "<schema>: schema must be an object or boolean"
    schema_type = schema.get("type")
    if schema_type is not None:
        if isinstance(schema_type, str):
            if schema_type not in _JSON_SCHEMA_TYPES:
                return f"<schema>.type: unsupported JSON Schema type"
        elif isinstance(schema_type, list):
            for t in schema_type:
                if t not in _JSON_SCHEMA_TYPES:
                    return f"<schema>.type: unsupported JSON Schema type"
    return None


def apply_json_schema_defaults(schema: Any, value: Any) -> Any:
    if not isinstance(value, dict) or not _is_record(schema):
        return value
    properties = schema.get("properties")
    if _is_record(properties):
        for key, prop_schema in properties.items():
            if key not in value and isinstance(prop_schema, dict) and "default" in prop_schema:
                value[key] = prop_schema["default"]
    return value
