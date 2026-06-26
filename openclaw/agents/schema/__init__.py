"""Shared schema helpers for agent tools.

Mirrors src/agents/schema/string-enum.ts and typebox.ts.
Python uses plain dicts for JSON Schema instead of TypeBox.
"""

from __future__ import annotations

from typing import Any

CHANNEL_TARGET_DESCRIPTION = "Channel target (channel:accountId or channel name)"
CHANNEL_TARGETS_DESCRIPTION = "Array of channel targets"


def string_enum(
    values: list[str],
    options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a flat string enum schema (avoids anyOf for provider compatibility)."""
    options = options or {}
    result: dict[str, Any] = {"type": "string"}
    if values:
        result["enum"] = list(values)
    result.update(options)
    return result


def optional_string_enum(
    values: list[str],
    options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build an optional string enum schema."""
    schema = string_enum(values, options)
    return {"anyOf": [schema, {"type": "null"}]}


def channel_target_schema(description: str | None = None) -> dict[str, Any]:
    """Build a schema for one outbound channel target."""
    return {"type": "string", "description": description or CHANNEL_TARGET_DESCRIPTION}


def channel_targets_schema(description: str | None = None) -> dict[str, Any]:
    """Build a schema for multiple outbound channel targets."""
    return {
        "type": "array",
        "items": channel_target_schema(description=description or CHANNEL_TARGETS_DESCRIPTION),
    }


def optional_finite_number_schema(options: dict[str, Any] | None = None) -> dict[str, Any]:
    """Build an optional finite number schema."""
    options = options or {}
    return {"anyOf": [{"type": "number", **options}, {"type": "null"}]}


def optional_positive_integer_schema(options: dict[str, Any] | None = None) -> dict[str, Any]:
    """Build an optional positive integer schema."""
    options = options or {}
    return {"anyOf": [{"type": "integer", "minimum": 1, **options}, {"type": "null"}]}


def optional_non_negative_integer_schema(options: dict[str, Any] | None = None) -> dict[str, Any]:
    """Build an optional non-negative integer schema."""
    options = options or {}
    return {"anyOf": [{"type": "integer", "minimum": 0, **options}, {"type": "null"}]}
