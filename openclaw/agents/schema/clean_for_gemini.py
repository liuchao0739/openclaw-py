"""Scrub/normalize tool JSON schemas for Gemini / Cloud Code Assist validators."""

from __future__ import annotations

import copy
from typing import Any

GEMINI_UNSUPPORTED_SCHEMA_KEYWORDS = frozenset(
    {
        "patternProperties",
        "additionalProperties",
        "$schema",
        "$id",
        "$ref",
        "$defs",
        "definitions",
        "examples",
        "minLength",
        "maxLength",
        "minimum",
        "maximum",
        "multipleOf",
        "pattern",
        "format",
        "minItems",
        "maxItems",
        "uniqueItems",
        "minProperties",
        "maxProperties",
        "not",
    }
)

_SCHEMA_META_KEYS = ("description", "title", "default")


def _copy_schema_meta(from_obj: dict[str, Any], to_obj: dict[str, Any]) -> None:
    for key in _SCHEMA_META_KEYS:
        if key in from_obj and from_obj[key] is not None:
            to_obj[key] = from_obj[key]


def _try_flatten_literal_any_of(
    variants: list[Any],
) -> dict[str, Any] | None:
    if not variants:
        return None
    all_values: list[Any] = []
    common_type: str | None = None
    for variant in variants:
        if not isinstance(variant, dict):
            return None
        v = variant
        literal_value: Any
        if "const" in v:
            literal_value = v["const"]
        elif isinstance(v.get("enum"), list) and len(v["enum"]) == 1:
            literal_value = v["enum"][0]
        else:
            return None
        variant_type = v.get("type")
        if not isinstance(variant_type, str):
            return None
        if common_type is None:
            common_type = variant_type
        elif common_type != variant_type:
            return None
        all_values.append(literal_value)
    if common_type and all_values:
        return {"type": common_type, "enum": all_values}
    return None


def _is_null_schema(variant: Any) -> bool:
    if not isinstance(variant, dict):
        return False
    record = variant
    if "const" in record and record["const"] is None:
        return True
    enum_val = record.get("enum")
    if isinstance(enum_val, list) and len(enum_val) == 1 and enum_val[0] is None:
        return True
    type_value = record.get("type")
    if type_value == "null":
        return True
    if isinstance(type_value, list) and len(type_value) == 1 and type_value[0] == "null":
        return True
    return False


def _strip_null_variants(variants: list[Any]) -> tuple[list[Any], bool]:
    if not variants:
        return variants, False
    non_null = [v for v in variants if not _is_null_schema(v)]
    return non_null, len(non_null) != len(variants)


def _extend_schema_defs(
    defs: dict[str, Any] | None,
    schema: dict[str, Any],
) -> dict[str, Any] | None:
    defs_entry = schema.get("$defs")
    legacy = schema.get("definitions")
    if not isinstance(defs_entry, dict) and not isinstance(legacy, dict):
        return defs
    next_defs = dict(defs) if defs else {}
    if isinstance(defs_entry, dict):
        next_defs.update(defs_entry)
    if isinstance(legacy, dict):
        next_defs.update(legacy)
    return next_defs


def _decode_json_pointer_segment(segment: str) -> str:
    return segment.replace("~1", "/").replace("~0", "~")


def _try_resolve_local_ref(ref: str, defs: dict[str, Any] | None) -> Any:
    if not defs:
        return None
    import re

    match = re.match(r"^#/(?:\$defs|definitions)/(.+)$", ref)
    if not match:
        return None
    name = _decode_json_pointer_segment(match.group(1) or "")
    if not name:
        return None
    return defs.get(name)


def _simplify_union_variants(
    obj: dict[str, Any],
    variants: list[Any],
) -> tuple[list[Any], Any | None]:
    non_null_variants, stripped = _strip_null_variants(list(variants))
    flattened = _try_flatten_literal_any_of(non_null_variants)
    if flattened:
        result = {"type": flattened["type"], "enum": flattened["enum"]}
        _copy_schema_meta(obj, result)
        return non_null_variants, result
    if stripped and len(non_null_variants) == 1:
        lone = non_null_variants[0]
        if isinstance(lone, dict):
            result = dict(lone)
            _copy_schema_meta(obj, result)
            return non_null_variants, result
        return non_null_variants, lone
    return (non_null_variants if stripped else variants), None


def _sanitize_required_fields(schema: dict[str, Any]) -> dict[str, Any]:
    required = schema.get("required")
    if not isinstance(required, list):
        return schema
    props = schema.get("properties")
    if not isinstance(props, dict):
        if schema.get("type") == "object":
            schema.pop("required", None)
        return schema
    filtered = [k for k in required if isinstance(k, str) and k in props]
    if filtered:
        schema["required"] = filtered
    else:
        schema.pop("required", None)
    return schema


def _flatten_union_fallback(
    obj: dict[str, Any],
    variants: list[Any],
) -> dict[str, Any] | None:
    objects = [v for v in variants if isinstance(v, dict)]
    if not objects:
        return None
    types = {v.get("type") for v in objects if v.get("type")}
    if len(objects) == 1:
        merged = dict(objects[0])
        _copy_schema_meta(obj, merged)
        return merged
    if len(types) == 1:
        merged: dict[str, Any] = {"type": next(iter(types))}
        _copy_schema_meta(obj, merged)
        return merged
    first = objects[0]
    if first.get("type"):
        merged = {"type": first["type"]}
        _copy_schema_meta(obj, merged)
        return merged
    merged = {}
    _copy_schema_meta(obj, merged)
    return merged


def _clean_schema_for_gemini_with_defs(
    schema: Any,
    defs: dict[str, Any] | None,
    ref_stack: set[str] | None,
) -> Any:
    if schema is None or not isinstance(schema, (dict, list)):
        return schema
    if isinstance(schema, list):
        return [_clean_schema_for_gemini_with_defs(item, defs, ref_stack) for item in schema]

    obj = schema
    next_defs = _extend_schema_defs(defs, obj)

    ref_value = obj.get("$ref")
    if isinstance(ref_value, str):
        if ref_stack and ref_value in ref_stack:
            return {}
        resolved = _try_resolve_local_ref(ref_value, next_defs)
        if resolved is not None:
            next_ref_stack = set(ref_stack) if ref_stack else set()
            next_ref_stack.add(ref_value)
            cleaned = _clean_schema_for_gemini_with_defs(resolved, next_defs, next_ref_stack)
            if not isinstance(cleaned, dict):
                return cleaned
            result = dict(cleaned)
            _copy_schema_meta(obj, result)
            return result
        result: dict[str, Any] = {}
        _copy_schema_meta(obj, result)
        return result

    has_any_of = "anyOf" in obj and isinstance(obj["anyOf"], list)
    has_one_of = "oneOf" in obj and isinstance(obj["oneOf"], list)
    cleaned_any_of: list[Any] | None = None
    cleaned_one_of: list[Any] | None = None
    if has_any_of:
        cleaned_any_of = [
            _clean_schema_for_gemini_with_defs(v, next_defs, ref_stack) for v in obj["anyOf"]
        ]
    if has_one_of:
        cleaned_one_of = [
            _clean_schema_for_gemini_with_defs(v, next_defs, ref_stack) for v in obj["oneOf"]
        ]

    if has_any_of and cleaned_any_of is not None:
        simplified_variants, simplified = _simplify_union_variants(obj, cleaned_any_of)
        cleaned_any_of = simplified_variants
        if simplified is not None:
            return simplified

    if has_one_of and cleaned_one_of is not None:
        simplified_variants, simplified = _simplify_union_variants(obj, cleaned_one_of)
        cleaned_one_of = simplified_variants
        if simplified is not None:
            return simplified

    cleaned: dict[str, Any] = {}
    for key, value in obj.items():
        if key in GEMINI_UNSUPPORTED_SCHEMA_KEYWORDS:
            continue
        if key == "const":
            cleaned["enum"] = [value]
            continue
        if key == "required" and isinstance(value, list) and len(value) == 0:
            continue
        if key == "type" and (has_any_of or has_one_of):
            continue
        if key == "type" and isinstance(value, list) and all(isinstance(e, str) for e in value):
            types = [e for e in value if e != "null"]
            cleaned["type"] = types[0] if len(types) == 1 else types
            continue
        if key == "properties":
            if isinstance(value, dict):
                cleaned[key] = {
                    k: _clean_schema_for_gemini_with_defs(v, next_defs, ref_stack)
                    for k, v in value.items()
                }
            else:
                cleaned[key] = {}
        elif key == "items" and value:
            if isinstance(value, list):
                cleaned[key] = [
                    _clean_schema_for_gemini_with_defs(entry, next_defs, ref_stack)
                    for entry in value
                ]
            elif isinstance(value, dict):
                cleaned[key] = _clean_schema_for_gemini_with_defs(value, next_defs, ref_stack)
            else:
                cleaned[key] = value
        elif key == "anyOf" and isinstance(value, list):
            cleaned[key] = cleaned_any_of or [
                _clean_schema_for_gemini_with_defs(v, next_defs, ref_stack) for v in value
            ]
        elif key == "oneOf" and isinstance(value, list):
            cleaned[key] = cleaned_one_of or [
                _clean_schema_for_gemini_with_defs(v, next_defs, ref_stack) for v in value
            ]
        elif key == "allOf" and isinstance(value, list):
            cleaned[key] = [
                _clean_schema_for_gemini_with_defs(v, next_defs, ref_stack) for v in value
            ]
        else:
            cleaned[key] = value

    if isinstance(cleaned.get("anyOf"), list):
        flattened = _flatten_union_fallback(cleaned, cleaned["anyOf"])
        if flattened:
            return _sanitize_required_fields(flattened)
    if isinstance(cleaned.get("oneOf"), list):
        flattened = _flatten_union_fallback(cleaned, cleaned["oneOf"])
        if flattened:
            return _sanitize_required_fields(flattened)

    return _sanitize_required_fields(cleaned)


def clean_schema_for_gemini(schema: Any) -> Any:
    if schema is None or not isinstance(schema, (dict, list)):
        return schema
    if isinstance(schema, list):
        return [clean_schema_for_gemini(item) for item in schema]
    defs = _extend_schema_defs(None, schema)
    return _clean_schema_for_gemini_with_defs(schema, defs, None)