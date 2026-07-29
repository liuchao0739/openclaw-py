import copy
import json
import math
import re
from typing import Any, Dict, Iterator, List, Optional, Union

from .types import Tool, ToolCall

JSON_NUMBER_TOKEN_RE = re.compile(
    r"^[+-]?(?:(?:\d+\.?\d*)|(?:\.\d+))(?:e[+-]?\d+)?$",
    re.IGNORECASE,
)


def _is_record(value: Any) -> bool:
    return isinstance(value, dict)


def _is_json_schema_object(value: Any) -> bool:
    return _is_record(value)


def _is_finite_number(value: Any) -> bool:
    if isinstance(value, bool):
        return False
    if isinstance(value, int):
        return True
    if isinstance(value, float):
        return math.isfinite(value)
    return False


def _is_integer(value: Any) -> bool:
    if isinstance(value, bool):
        return False
    if isinstance(value, int):
        return True
    if isinstance(value, float) and math.isfinite(value) and value.is_integer():
        return True
    return False


def _is_safe_integer(value: Any) -> bool:
    if not _is_integer(value):
        return False
    return -(2**53 - 1) <= value <= (2**53 - 1)


def _get_schema_types(schema: Any) -> List[str]:
    schema_type = schema.get("type") if _is_record(schema) else None
    if isinstance(schema_type, str):
        return [schema_type]
    if isinstance(schema_type, list):
        return [t for t in schema_type if isinstance(t, str)]
    return []


def _matches_json_type(value: Any, type_name: str) -> bool:
    if type_name == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if type_name == "integer":
        return _is_integer(value)
    if type_name == "boolean":
        return isinstance(value, bool)
    if type_name == "string":
        return isinstance(value, str)
    if type_name == "null":
        return value is None
    if type_name == "array":
        return isinstance(value, list)
    if type_name == "object":
        return _is_record(value)
    return False


def _parse_json_number_string(value: str) -> Optional[float]:
    trimmed = value.strip()
    if not trimmed or not JSON_NUMBER_TOKEN_RE.match(trimmed):
        return None
    try:
        parsed = float(trimmed)
        if math.isfinite(parsed):
            return parsed
    except ValueError:
        pass
    return None


def _parse_json_integer_string(value: str) -> Optional[int]:
    parsed = _parse_json_number_string(value)
    if parsed is not None and _is_safe_integer(parsed):
        return int(parsed)
    return None


def _coerce_primitive_by_type(value: Any, type_name: str) -> Any:
    if type_name == "number":
        if value is None:
            return 0
        if isinstance(value, str) and value.strip():
            parsed = _parse_json_number_string(value)
            if parsed is not None:
                return parsed
        if isinstance(value, bool):
            return 1 if value else 0
        return value
    if type_name == "integer":
        if value is None:
            return 0
        if isinstance(value, str) and value.strip():
            parsed = _parse_json_integer_string(value)
            if parsed is not None:
                return parsed
        if isinstance(value, bool):
            return 1 if value else 0
        return value
    if type_name == "boolean":
        if value is None:
            return False
        if isinstance(value, str):
            if value == "true":
                return True
            if value == "false":
                return False
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            if value == 1:
                return True
            if value == 0:
                return False
        return value
    if type_name == "string":
        if value is None:
            return ""
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return str(value)
        if isinstance(value, bool):
            return "true" if value else "false"
        return value
    if type_name == "null":
        if value == "" or value == 0 or value is False:
            return None
        return value
    return value


def _apply_schema_object_coercion(value: Dict[str, Any], schema: Any) -> None:
    properties = schema.get("properties")
    defined_keys = set(properties.keys()) if _is_record(properties) else set()

    if _is_record(properties):
        for key, property_schema in properties.items():
            if key in value:
                value[key] = _coerce_with_json_schema(value[key], property_schema)

    additional = schema.get("additionalProperties")
    if _is_json_schema_object(additional):
        for key, property_value in value.items():
            if key not in defined_keys:
                value[key] = _coerce_with_json_schema(property_value, additional)


def _apply_schema_array_coercion(value: List[Any], schema: Any) -> None:
    items = schema.get("items")
    if isinstance(items, list):
        for index in range(len(value)):
            if index < len(items):
                value[index] = _coerce_with_json_schema(value[index], items[index])
        return

    if _is_json_schema_object(items):
        for index in range(len(value)):
            value[index] = _coerce_with_json_schema(value[index], items)


def _coerce_with_union_schema(value: Any, schemas: List[Any]) -> Any:
    for schema in schemas:
        candidate = copy.deepcopy(value)
        coerced = _coerce_with_json_schema(candidate, schema)
        if _check_schema(schema, coerced):
            return coerced
    return value


def _coerce_with_json_schema(value: Any, schema: Any) -> Any:
    if not _is_json_schema_object(schema):
        return value

    next_value = value

    all_of = schema.get("allOf")
    if isinstance(all_of, list):
        for nested in all_of:
            next_value = _coerce_with_json_schema(next_value, nested)

    any_of = schema.get("anyOf")
    if isinstance(any_of, list):
        next_value = _coerce_with_union_schema(next_value, any_of)

    one_of = schema.get("oneOf")
    if isinstance(one_of, list):
        next_value = _coerce_with_union_schema(next_value, one_of)

    schema_types = _get_schema_types(schema)
    matches_union_member = (
        len(schema_types) > 1
        and any(_matches_json_type(next_value, t) for t in schema_types)
    )
    if len(schema_types) > 0 and not matches_union_member:
        for schema_type in schema_types:
            candidate = _coerce_primitive_by_type(next_value, schema_type)
            if candidate is not next_value:
                next_value = candidate
                break

    if "object" in schema_types and _is_record(next_value):
        _apply_schema_object_coercion(next_value, schema)

    if "array" in schema_types and isinstance(next_value, list):
        _apply_schema_array_coercion(next_value, schema)

    return next_value


def _check_schema(schema: Any, value: Any) -> bool:
    for _ in _iter_schema_errors(schema, value, ""):
        return False
    return True


def _iter_schema_errors(schema: Any, value: Any, path: str) -> Iterator[dict]:
    if not _is_record(schema):
        return

    all_of = schema.get("allOf")
    if isinstance(all_of, list):
        for sub_schema in all_of:
            yield from _iter_schema_errors(sub_schema, value, path)

    any_of = schema.get("anyOf")
    if isinstance(any_of, list):
        if not any(_check_schema(sub, value) for sub in any_of):
            yield {
                "keyword": "anyOf",
                "instancePath": path,
                "message": "Value does not match any schema in anyOf",
                "params": {},
            }

    one_of = schema.get("oneOf")
    if isinstance(one_of, list):
        matches = sum(1 for sub in one_of if _check_schema(sub, value))
        if matches != 1:
            yield {
                "keyword": "oneOf",
                "instancePath": path,
                "message": "Value does not match exactly one schema in oneOf",
                "params": {},
            }

    schema_types = _get_schema_types(schema)
    if schema_types and not any(_matches_json_type(value, t) for t in schema_types):
        yield {
            "keyword": "type",
            "instancePath": path,
            "message": f"Expected type {'/'.join(schema_types)}",
            "params": {"type": schema_types},
        }

    enum = schema.get("enum")
    if isinstance(enum, list):
        if value not in enum:
            yield {
                "keyword": "enum",
                "instancePath": path,
                "message": f"Value not in enum: {enum}",
                "params": {"allowedValues": enum},
            }

    if _is_record(value):
        required = schema.get("required")
        if isinstance(required, list):
            for prop in required:
                if prop not in value:
                    yield {
                        "keyword": "required",
                        "instancePath": path,
                        "message": f"Missing required property: {prop}",
                        "params": {"requiredProperties": [prop]},
                    }

        properties = schema.get("properties")
        if _is_record(properties):
            for key, prop_schema in properties.items():
                if key in value:
                    child_path = f"{path}/{key}"
                    yield from _iter_schema_errors(prop_schema, value[key], child_path)

        additional = schema.get("additionalProperties")
        if additional is False:
            for key in value:
                if key not in (properties or {}):
                    yield {
                        "keyword": "additionalProperties",
                        "instancePath": f"{path}/{key}",
                        "message": f"Additional property not allowed: {key}",
                        "params": {"additionalProperty": key},
                    }
        elif _is_json_schema_object(additional):
            for key, val in value.items():
                if key not in (properties or {}):
                    yield from _iter_schema_errors(additional, val, f"{path}/{key}")

    if isinstance(value, list):
        items = schema.get("items")
        if _is_json_schema_object(items):
            for i, item in enumerate(value):
                yield from _iter_schema_errors(items, item, f"{path}/{i}")
        elif isinstance(items, list):
            for i, item_schema in enumerate(items):
                if i < len(value):
                    yield from _iter_schema_errors(item_schema, value[i], f"{path}/{i}")


def _format_validation_path(error: dict) -> str:
    if error.get("keyword") == "required":
        required_properties = error.get("params", {}).get("requiredProperties")
        if required_properties:
            required_property = required_properties[0]
            base_path = error.get("instancePath", "").lstrip("/").replace("/", ".")
            return f"{base_path}.{required_property}" if base_path else required_property
    path = error.get("instancePath", "").lstrip("/").replace("/", ".")
    return path or "root"


def validate_tool_call(tools: List[Tool], tool_call: ToolCall) -> Any:
    tool_name = tool_call.get("name", "")
    tool = next((t for t in tools if t.get("name") == tool_name), None)
    if tool is None:
        raise ValueError(f'Tool "{tool_name}" not found')
    return validate_tool_arguments(tool, tool_call)


def validate_tool_arguments(tool: Tool, tool_call: ToolCall) -> Any:
    tool_name = tool_call.get("name", "")
    schema = tool.get("parameters", {})

    args = copy.deepcopy(tool_call.get("arguments", {}))

    if _is_json_schema_object(schema):
        coerced = _coerce_with_json_schema(args, schema)
        if coerced is not args:
            if _is_record(args) and _is_record(coerced):
                args.clear()
                args.update(coerced)
            else:
                if _check_schema(schema, coerced):
                    return coerced

    if _check_schema(schema, args):
        return args

    errors = "\n".join(
        f"  - {_format_validation_path(error)}: {error.get('message', '')}"
        for error in _iter_schema_errors(schema, args, "")
    )
    if not errors:
        errors = "Unknown validation error"

    raise ValueError(
        f'Validation failed for tool "{tool_name}":\n{errors}\n\nReceived arguments:\n{json.dumps(tool_call.get("arguments", {}), indent=2)}'
    )
