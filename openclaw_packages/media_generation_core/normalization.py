"""Media generation normalization metadata types and helpers."""

from __future__ import annotations

from typing import TypedDict, TypeVar

MediaNormalizationValue = str | int | bool
TValue = TypeVar("TValue", str, int, bool)


class MediaNormalizationEntry(TypedDict, total=False):
    requested: TValue
    applied: TValue
    derived_from: str
    supported_values: list[TValue]


class MediaGenerationNormalizationMetadataInput(TypedDict, total=False):
    size: MediaNormalizationEntry[str]
    aspect_ratio: MediaNormalizationEntry[str]
    resolution: MediaNormalizationEntry[str]
    duration_seconds: MediaNormalizationEntry[int]


def has_media_normalization_entry(
    entry: MediaNormalizationEntry[TValue] | None,
) -> bool:
    """True when a normalization entry contains any user-visible normalization metadata."""
    if not entry:
        return False
    supported_values = entry.get("supported_values")
    return (
        entry.get("requested") is not None
        or entry.get("applied") is not None
        or entry.get("derived_from") is not None
        or bool(supported_values)
    )


__all__ = [
    "MediaGenerationNormalizationMetadataInput",
    "MediaNormalizationEntry",
    "MediaNormalizationValue",
    "has_media_normalization_entry",
]
