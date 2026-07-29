from typing import Optional, TypedDict

from .string import normalize_optional_string


class ParsedGenerationModelRef(TypedDict):
    provider: str
    model: str


def parse_generation_model_ref(raw: Optional[str]) -> Optional[ParsedGenerationModelRef]:
    trimmed = normalize_optional_string(raw)
    if not trimmed:
        return None
    slash_index = trimmed.find("/")
    if slash_index <= 0 or slash_index == len(trimmed) - 1:
        return None
    provider = normalize_optional_string(trimmed[:slash_index])
    model = normalize_optional_string(trimmed[slash_index + 1:])
    if provider and model:
        return {"provider": provider, "model": model}
    return None
