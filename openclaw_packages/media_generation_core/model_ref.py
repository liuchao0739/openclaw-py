"""Media generation model reference parsing."""

from __future__ import annotations

from typing import TypedDict

from openclaw.packages.normalization_core import normalize_optional_string

__all__ = ["ParsedGenerationModelRef", "parse_generation_model_ref"]


class ParsedGenerationModelRef(TypedDict):
    provider: str
    model: str


def parse_generation_model_ref(raw: str | None) -> ParsedGenerationModelRef | None:
    """Parse strict generation model refs and reject missing provider or model segments."""
    trimmed = normalize_optional_string(raw)
    if not trimmed:
        return None
    slash_index = trimmed.find("/")
    if slash_index <= 0 or slash_index == len(trimmed) - 1:
        return None
    provider = normalize_optional_string(trimmed[:slash_index])
    model = normalize_optional_string(trimmed[slash_index + 1 :])
    if provider and model:
        return {"provider": provider, "model": model}
    return None
