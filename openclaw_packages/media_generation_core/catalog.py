"""Media generation catalog contracts and static entry synthesis."""

from __future__ import annotations

from typing import Any, Literal, TypedDict

from .string import unique_trimmed_strings

__all__ = [
    "MediaGenerationCatalogEntry",
    "MediaGenerationCatalogKind",
    "MediaGenerationCatalogProvider",
    "MediaGenerationCatalogSource",
    "list_media_generation_provider_models",
    "synthesize_media_generation_catalog_entries",
]

MediaGenerationCatalogKind = Literal[
    "image_generation",
    "video_generation",
    "music_generation",
]
MediaGenerationCatalogSource = Literal["static", "live", "cache", "configured"]


class MediaGenerationCatalogEntry(TypedDict, total=False):
    kind: MediaGenerationCatalogKind
    provider: str
    model: str
    label: str
    source: MediaGenerationCatalogSource
    default: bool
    configured: bool
    capabilities: Any
    modes: list[str]
    auth_env_vars: list[str]
    docs_path: str
    fetched_at: int
    expires_at: int
    warnings: list[str]


class MediaGenerationCatalogProvider(TypedDict, total=False):
    id: str
    aliases: list[str]
    label: str
    default_model: str
    models: list[str]
    capabilities: Any


def _unique_models(provider: MediaGenerationCatalogProvider) -> list[str]:
    return unique_trimmed_strings([provider.get("default_model"), *(provider.get("models") or [])])


def synthesize_media_generation_catalog_entries(
    *,
    kind: MediaGenerationCatalogKind,
    provider: MediaGenerationCatalogProvider,
    modes: list[str] | None = None,
) -> list[MediaGenerationCatalogEntry]:
    """Synthesize static catalog entries from provider metadata."""
    default_model = unique_trimmed_strings([provider.get("default_model")])
    default_model_value = default_model[0] if default_model else None
    entries: list[MediaGenerationCatalogEntry] = []
    for model in _unique_models(provider):
        entry: MediaGenerationCatalogEntry = {
            "kind": kind,
            "provider": provider["id"],
            "model": model,
            "source": "static",
            "capabilities": provider["capabilities"],
        }
        if provider.get("label"):
            entry["label"] = provider["label"]
        if model == default_model_value:
            entry["default"] = True
        if modes is not None:
            entry["modes"] = modes
        entries.append(entry)
    return entries


def list_media_generation_provider_models(
    provider: MediaGenerationCatalogProvider,
) -> list[str]:
    """Return unique model ids exposed by a media generation provider."""
    return _unique_models(provider)
