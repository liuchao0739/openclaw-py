from typing import Any, Optional, Sequence, TypedDict, Union

MediaNormalizationValue = Union[str, int, float, bool]


class MediaNormalizationEntry(TypedDict, total=False):
    requested: MediaNormalizationValue
    applied: MediaNormalizationValue
    derivedFrom: str
    supportedValues: Sequence[MediaNormalizationValue]


class MediaGenerationNormalizationMetadataInput(TypedDict, total=False):
    size: MediaNormalizationEntry
    aspectRatio: MediaNormalizationEntry
    resolution: MediaNormalizationEntry
    durationSeconds: MediaNormalizationEntry


def has_media_normalization_entry(
    entry: Optional[MediaNormalizationEntry],
) -> bool:
    if not entry:
        return False
    return (
        entry.get("requested") is not None
        or entry.get("applied") is not None
        or entry.get("derivedFrom") is not None
        or len(entry.get("supportedValues") or []) > 0
    )
