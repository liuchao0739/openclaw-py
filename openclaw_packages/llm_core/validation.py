"""LLM Core tool argument validation.

Mirrors packages/llm-core/src/validation.ts.
"""

from __future__ import annotations

import copy
import json
import math
from dataclasses import dataclass
from typing import Any

from openclaw_packages.normalization_core import is_record
from openclaw_packages.normalization_core.number_coercion import (
    parse_strict_finite_number,
    parse_strict_integer,
)

TYPEBOX_KIND = "__typebox_kind__"


class JsonSchemaObject(dict[str, Any]):
    """Typed JSON schema object wrapper."""


@dataclass(frozen=True)
class ValidationErrorInfo:
    keyword: str
    instance_path: str
    message: str
    params: dict[str, Any]


class CompiledValidator:
    def __init__(self, schema: dict[str, Any]) -> None:
        self._schema = schema

    def check(self, value: Any) -> bool:
        return len(list(self.errors(value))) == 0

    def errors(self, value: Any) -> list[ValidationErrorInfo]:
        return _validate_value(value, self._schema, "")


_validator_cache: dict[str, CompiledValidator] = {}


def _is_json_schema_object(value: Any) -> bool:
    return is_record(value)


def _has_typebox_metadata(schema: Any) -> bool:
    return is_record(schema) and TYPEBOX_KIND in schema


def _get_schema_types(schema: JsonSchemaObject) -> list[str]:
    schema_type = schema.get("type")
    if isinstance(schema_type, str):
        return [schema_type]
    if isinstance(schema_type, list):
        return [entry for entry in schema_type if isinstance(entry, str)]
    return []


def _matches_json_type(value: Any, schema_type: str) -> bool:
    if schema_type == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if schema_type == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if schema_type == "boolean":
        return isinstance(value, bool)
    if schema_type == "string":
        return isinstance(value, str)
    if schema_type == "null":
        return value is None
    if schema_type == "array":
        return isinstance(value, list)
    if schema_type == "object":
        return is_record(value) and not isinstance(value, list)
    return False


def _is_validator_schema(value: Any) -> bool:
    return is_record(value)


def _get_validator(schema: dict[str, Any]) -> CompiledValidator:
    cache_key = json.dumps(schema, sort_keys=True, default=str)
    cached = _validator_cache.get(cache_key)
    if cached is not None:
        return cached
    validator = CompiledValidator(schema)
    _validator_cache[cache_key] = validator
    return validator


def _get_sub_schema_validator(schema: JsonSchemaObject) -> CompiledValidator | None:
    if not _is_validator_schema(schema):
        return None
    try:
        return _get_validator(schema)
    except (TypeError, ValueError, KeyError):
        return None


def _coerce_primitive_by_type(value: Any, schema_type: str) -> Any:
    if schema_type == "number":
        if value is None:
            return 0
        if isinstance(value, str) and value.strip() != "":
            parsed = parse_strict_finite_number(value)
            if parsed is not None:
                return parsed
        if isinstance(value, bool):
            return 1 if value else 0
        return value

    if schema_type == "integer":
        if value is None:
            return 0
        if isinstance(value, str) and value.strip() != "":
            parsed = parse_strict_integer(value)
            if parsed is not None:
                return parsed
        if isinstance(value, bool):
            return 1 if value else 0
        return value

    if schema_type == "boolean":
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

    if schema_type == "string":
        if value is None:
            return ""
        if isinstance(value, (int, float, bool)):
            return str(value)
        return value

    if schema_type == "null":
        if value in ("", 0, False):
            return None
        return value

    return value


def _apply_schema_object_coercion(value: dict[str, Any], schema: JsonSchemaObject) -> None:
    properties = schema.get("properties")
    defined_keys = set(properties.keys()) if isinstance(properties, dict) else set()

    if isinstance(properties, dict):
        for key, property_schema in properties.items():
            if key in value and _is_json_schema_object(property_schema):
                value[key] = _coerce_with_json_schema(value[key], property_schema)

    additional_properties = schema.get("additionalProperties")
    if _is_json_schema_object(additional_properties):
        for key, property_value in value.items():
            if key not in defined_keys:
                value[key] = _coerce_with_json_schema(property_value, additional_properties)


def _apply_schema_array_coercion(value: list[Any], schema: JsonSchemaObject) -> None:
    items = schema.get("items")
    if isinstance(items, list):
        for index, item_schema in enumerate(items):
            if index < len(value) and _is_json_schema_object(item_schema):
                value[index] = _coerce_with_json_schema(value[index], item_schema)
        return

    if _is_json_schema_object(items):
        for index in range(len(value)):
            value[index] = _coerce_with_json_schema(value[index], items)


def _coerce_with_union_schema(value: Any, schemas: list[JsonSchemaObject]) -> Any:
    for schema in schemas:
        candidate = copy.deepcopy(value)
        coerced = _coerce_with_json_schema(candidate, schema)
        validator = _get_sub_schema_validator(schema)
        if validator is not None and validator.check(coerced):
            return coerced
    return value


def _coerce_with_json_schema(value: Any, schema: JsonSchemaObject) -> Any:
    next_value = value

    all_of = schema.get("allOf")
    if isinstance(all_of, list):
        for nested in all_of:
            if _is_json_schema_object(nested):
                next_value = _coerce_with_json_schema(next_value, nested)

    any_of = schema.get("anyOf")
    if isinstance(any_of, list):
        next_value = _coerce_with_union_schema(
            next_value,
            [entry for entry in any_of if _is_json_schema_object(entry)],
        )

    one_of = schema.get("oneOf")
    if isinstance(one_of, list):
        next_value = _coerce_with_union_schema(
            next_value,
            [entry for entry in one_of if _is_json_schema_object(entry)],
        )

    schema_types = _get_schema_types(schema)
    matches_union_member = len(schema_types) > 1 and any(
        _matches_json_type(next_value, schema_type) for schema_type in schema_types
    )
    if schema_types and not matches_union_member:
        for schema_type in schema_types:
            candidate = _coerce_primitive_by_type(next_value, schema_type)
            if candidate is not next_value:
                next_value = candidate
                break

    if "object" in schema_types and is_record(next_value) and not isinstance(next_value, list):
        _apply_schema_object_coercion(next_value, schema)

    if "array" in schema_types and isinstance(next_value, list):
        _apply_schema_array_coercion(next_value, schema)

    return next_value


def _value_convert(schema: dict[str, Any], value: Any) -> None:
    """Conservative TypeBox Value.Convert parity for plain JSON schemas."""
    if not _is_json_schema_object(schema):
        return

    schema_types = _get_schema_types(schema)
    if "object" in schema_types and is_record(value) and not isinstance(value, list):
        properties = schema.get("properties")
        if isinstance(properties, dict):
            for key, property_schema in properties.items():
                if key in value and _is_json_schema_object(property_schema):
                    _value_convert(property_schema, value[key])
        return

    if "array" in schema_types and isinstance(value, list):
        items = schema.get("items")
        if _is_json_schema_object(items):
            for index in range(len(value)):
                _value_convert(items, value[index])
        elif isinstance(items, list):
            for index, item_schema in enumerate(items):
                if index < len(value) and _is_json_schema_object(item_schema):
                    _value_convert(item_schema, value[index])


def _join_path(base_path: str, segment: str) -> str:
    return f"{base_path}.{segment}" if base_path else segment


def _validate_value(
    value: Any,
    schema: JsonSchemaObject,
    instance_path: str,
) -> list[ValidationErrorInfo]:
    errors: list[ValidationErrorInfo] = []

    all_of = schema.get("allOf")
    if isinstance(all_of, list):
        for nested in all_of:
            if _is_json_schema_object(nested):
                errors.extend(_validate_value(value, nested, instance_path))
        if errors:
            return errors

    any_of = schema.get("anyOf")
    if isinstance(any_of, list):
        nested_schemas = [entry for entry in any_of if _is_json_schema_object(entry)]
        if nested_schemas and not any(
            len(_validate_value(value, nested, instance_path)) == 0 for nested in nested_schemas
        ):
            errors.append(
                ValidationErrorInfo(
                    keyword="anyOf",
                    instance_path=instance_path,
                    message="Value should match one schema in anyOf",
                    params={},
                )
            )
        return errors

    one_of = schema.get("oneOf")
    if isinstance(one_of, list):
        nested_schemas = [entry for entry in one_of if _is_json_schema_object(entry)]
        matches = [
            nested
            for nested in nested_schemas
            if len(_validate_value(value, nested, instance_path)) == 0
        ]
        if len(matches) != 1:
            errors.append(
                ValidationErrorInfo(
                    keyword="oneOf",
                    instance_path=instance_path,
                    message="Value should match exactly one schema in oneOf",
                    params={},
                )
            )
        return errors

    schema_types = _get_schema_types(schema)
    if schema_types and not any(
        _matches_json_type(value, schema_type) for schema_type in schema_types
    ):
        expected = ", ".join(schema_types)
        errors.append(
            ValidationErrorInfo(
                keyword="type",
                instance_path=instance_path,
                message=f"Expected {expected}",
                params={"type": schema_types},
            )
        )
        return errors

    if "object" in schema_types and is_record(value) and not isinstance(value, list):
        properties = schema.get("properties")
        defined_keys = set(properties.keys()) if isinstance(properties, dict) else set()

        required = schema.get("required")
        if isinstance(required, list):
            for required_property in required:
                if isinstance(required_property, str) and required_property not in value:
                    errors.append(
                        ValidationErrorInfo(
                            keyword="required",
                            instance_path=instance_path,
                            message=f"Required property '{required_property}'",
                            params={"requiredProperties": [required_property]},
                        )
                    )

        if isinstance(properties, dict):
            for key, property_schema in properties.items():
                if key in value and _is_json_schema_object(property_schema):
                    errors.extend(
                        _validate_value(value[key], property_schema, _join_path(instance_path, key))
                    )

        additional_properties = schema.get("additionalProperties")
        if additional_properties is False:
            for key in value:
                if key not in defined_keys:
                    errors.append(
                        ValidationErrorInfo(
                            keyword="additionalProperties",
                            instance_path=_join_path(instance_path, key),
                            message="Additional property not allowed",
                            params={},
                        )
                    )
        elif _is_json_schema_object(additional_properties):
            for key, property_value in value.items():
                if key not in defined_keys:
                    errors.extend(
                        _validate_value(
                            property_value,
                            additional_properties,
                            _join_path(instance_path, key),
                        )
                    )

    if "array" in schema_types and isinstance(value, list):
        items = schema.get("items")
        if _is_json_schema_object(items):
            for index, item in enumerate(value):
                errors.extend(_validate_value(item, items, f"{instance_path}/{index}"))
        elif isinstance(items, list):
            for index, item_schema in enumerate(items):
                if index < len(value) and _is_json_schema_object(item_schema):
                    errors.extend(
                        _validate_value(value[index], item_schema, f"{instance_path}/{index}")
                    )

    if (
        "number" in schema_types
        and isinstance(value, (int, float))
        and not isinstance(value, bool)
        and (math.isnan(value) or math.isinf(value))
    ):
        errors.append(
            ValidationErrorInfo(
                keyword="type",
                instance_path=instance_path,
                message="Expected finite number",
                params={},
            )
        )

    return errors


def _format_validation_path(error: ValidationErrorInfo) -> str:
    if error.keyword == "required":
        required_properties = error.params.get("requiredProperties")
        if isinstance(required_properties, list) and required_properties:
            required_property = required_properties[0]
            if isinstance(required_property, str):
                base_path = error.instance_path.replace("/", ".")
                return f"{base_path}.{required_property}" if base_path else required_property
    path = error.instance_path.replace("/", ".").lstrip(".")
    return path or "root"


def validate_tool_call(tools: list[dict[str, Any]], tool_call: dict[str, Any]) -> Any:
    """Find the target tool and validate/coerce a model-emitted tool call."""
    tool_name = tool_call.get("name")
    tool = next((entry for entry in tools if entry.get("name") == tool_name), None)
    if tool is None:
        raise ValueError(f'Tool "{tool_name}" not found')
    return validate_tool_arguments(tool, tool_call)


def validate_tool_arguments(tool: dict[str, Any], tool_call: dict[str, Any]) -> Any:
    """Validate tool arguments against TypeBox or plain JSON-schema parameters."""
    args = copy.deepcopy(tool_call.get("arguments", {}))
    parameters = tool.get("parameters", {})
    if not isinstance(parameters, dict):
        raise TypeError(f'Validation failed for tool "{tool_call.get("name")}": invalid schema')

    _value_convert(parameters, args)

    validator = _get_validator(parameters)
    if not _has_typebox_metadata(parameters) and _is_json_schema_object(parameters):
        coerced = _coerce_with_json_schema(args, parameters)
        if coerced is not args:
            if is_record(args) and is_record(coerced):
                for key in list(args.keys()):
                    del args[key]
                args.update(coerced)
            else:
                return coerced if validator.check(coerced) else args

    if validator.check(args):
        return args

    validation_errors = validator.errors(args)
    error_lines = "\n".join(
        f"  - {_format_validation_path(error)}: {error.message}" for error in validation_errors
    )
    if not error_lines:
        error_lines = "Unknown validation error"

    raise ValueError(
        f'Validation failed for tool "{tool_call.get("name")}":\n{error_lines}\n\n'
        f"Received arguments:\n{json.dumps(tool_call.get('arguments', {}), indent=2)}"
    )


__all__ = [
    "validate_tool_arguments",
    "validate_tool_call",
]
