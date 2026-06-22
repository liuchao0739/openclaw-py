"""Shared JSON-schema helpers for agent tools (TypeBox parity)."""

from __future__ import annotations

from typing import Any

from openclaw.agents.schema.string_enum import optional_string_enum, string_enum

CHANNEL_TARGET_DESCRIPTION = (
    "Outbound channel target (channel id, user id, or routing address accepted by the channel)."
)
CHANNEL_TARGETS_DESCRIPTION = (
    "One or more outbound channel targets for multi-recipient delivery."
)


def channel_target_schema(*, description: str | None = None) -> dict[str, Any]:
    return {
        "type": "string",
        "description": description if description is not None else CHANNEL_TARGET_DESCRIPTION,
    }


def channel_targets_schema(*, description: str | None = None) -> dict[str, Any]:
    return {
        "type": "array",
        "items": channel_target_schema(
            description=description if description is not None else CHANNEL_TARGETS_DESCRIPTION,
        ),
    }


def optional_finite_number_schema(
    *,
    description: str | None = None,
    deprecated: bool | None = None,
    minimum: float | None = None,
    maximum: float | None = None,
    exclusive_minimum: float | None = None,
    exclusive_maximum: float | None = None,
) -> dict[str, Any]:
    inner: dict[str, Any] = {"type": "number"}
    if description is not None:
        inner["description"] = description
    if deprecated is not None:
        inner["deprecated"] = deprecated
    if minimum is not None:
        inner["minimum"] = minimum
    if maximum is not None:
        inner["maximum"] = maximum
    if exclusive_minimum is not None:
        inner["exclusiveMinimum"] = exclusive_minimum
    if exclusive_maximum is not None:
        inner["exclusiveMaximum"] = exclusive_maximum
    return inner


def optional_positive_integer_schema(
    *,
    description: str | None = None,
    maximum: int | None = None,
) -> dict[str, Any]:
    inner: dict[str, Any] = {"type": "integer", "minimum": 1}
    if description is not None:
        inner["description"] = description
    if maximum is not None:
        inner["maximum"] = maximum
    return inner


def optional_non_negative_integer_schema(
    *,
    description: str | None = None,
    maximum: int | None = None,
) -> dict[str, Any]:
    inner: dict[str, Any] = {"type": "integer", "minimum": 0}
    if description is not None:
        inner["description"] = description
    if maximum is not None:
        inner["maximum"] = maximum
    return inner


__all__ = [
    "CHANNEL_TARGET_DESCRIPTION",
    "CHANNEL_TARGETS_DESCRIPTION",
    "channel_target_schema",
    "channel_targets_schema",
    "optional_finite_number_schema",
    "optional_non_negative_integer_schema",
    "optional_positive_integer_schema",
    "optional_string_enum",
    "string_enum",
]