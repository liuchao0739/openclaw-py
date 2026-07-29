from typing import Any, List, Literal, Optional, Sequence, TypedDict

from .string import unique_trimmed_strings

MediaGenerationCatalogKind = Literal["image_generation", "video_generation", "music_generation"]
MediaGenerationCatalogSource = Literal["static", "live", "cache", "configured"]


class MediaGenerationCatalogEntry(TypedDict, total=False):
    kind: MediaGenerationCatalogKind
    provider: str
    model: str
    source: MediaGenerationCatalogSource
    default: bool
    configured: bool
    capabilities: Any
    modes: Sequence[str]
    authEnvVars: Sequence[str]
    docsPath: str
    fetchedAt: int
    expiresAt: int
    warnings: Sequence[str]


class MediaGenerationCatalogProvider(TypedDict, total=False):
    id: str
    aliases: Sequence[str]
    label: str
    defaultModel: str
    models: Sequence[str]
    capabilities: Any


def _unique_models(provider) -> List[str]:
    default_model = provider.get("defaultModel") if isinstance(provider, dict) else None
    models = provider.get("models") if isinstance(provider, dict) else None
    return unique_trimmed_strings([default_model, *(models or [])])


def synthesize_media_generation_catalog_entries(
    kind: MediaGenerationCatalogKind,
    provider: MediaGenerationCatalogProvider,
    modes: Optional[Sequence[str]] = None,
) -> List[MediaGenerationCatalogEntry]:
    default_model = unique_trimmed_strings([provider.get("defaultModel")])[0] if provider.get("defaultModel") else None
    result: List[MediaGenerationCatalogEntry] = []
    for model in _unique_models(provider):
        entry: MediaGenerationCatalogEntry = {
            "kind": kind,
            "provider": provider["id"],
            "model": model,
            "source": "static",
            "capabilities": provider.get("capabilities"),
        }
        if provider.get("label"):
            entry["label"] = provider["label"]
        if model == default_model:
            entry["default"] = True
        if modes:
            entry["modes"] = modes
        result.append(entry)
    return result


def list_media_generation_provider_models(provider) -> List[str]:
    return _unique_models(provider)
