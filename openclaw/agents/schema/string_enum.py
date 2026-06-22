"""Provider-safe string enum schema helpers (flat enum, not anyOf unions)."""

from __future__ import annotations

from typing import Any, Mapping, Sequence, TypeVar, overload

T = TypeVar("T", bound=str)


def _enum_values(values: Sequence[T] | Mapping[str, T]) -> list[T]:
    if isinstance(values, Mapping):
        return [v for v in values.values() if isinstance(v, str)]
    return list(values)


def string_enum(
    values: Sequence[T] | Mapping[str, T],
    *,
    description: str | None = None,
    title: str | None = None,
    default: T | None = None,
    deprecated: bool | None = None,
) -> dict[str, Any]:
    enum_values = _enum_values(values)
    schema: dict[str, Any] = {"type": "string"}
    if enum_values:
        schema["enum"] = list(enum_values)
    if description is not None:
        schema["description"] = description
    if title is not None:
        schema["title"] = title
    if default is not None:
        schema["default"] = default
    if deprecated is not None:
        schema["deprecated"] = deprecated
    return schema


def optional_string_enum(
    values: Sequence[T] | Mapping[str, T],
    **options: Any,
) -> dict[str, Any]:
    return string_enum(values, **options)