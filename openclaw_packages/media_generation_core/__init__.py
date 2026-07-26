"""Public barrel for media-generation shared model refs and catalog helpers.

Mirrors packages/media-generation-core/src/index.ts.
"""

from __future__ import annotations

from .capability_model_ref import (
    CapabilityModelProviderCandidate,
    CapabilityModelRef,
    find_capability_provider_by_id,
    resolve_capability_model_ref_for_providers,
    resolve_capability_provider_model_only_ref,
)
from .catalog import (
    MediaGenerationCatalogEntry,
    MediaGenerationCatalogKind,
    MediaGenerationCatalogProvider,
    MediaGenerationCatalogSource,
    list_media_generation_provider_models,
    synthesize_media_generation_catalog_entries,
)
from .model_ref import ParsedGenerationModelRef, parse_generation_model_ref
from .normalization import (
    MediaGenerationNormalizationMetadataInput,
    MediaNormalizationEntry,
    MediaNormalizationValue,
    has_media_normalization_entry,
)
from .string import normalize_optional_string, unique_trimmed_strings

__all__ = [
    "CapabilityModelProviderCandidate",
    "CapabilityModelRef",
    "MediaGenerationCatalogEntry",
    "MediaGenerationCatalogKind",
    "MediaGenerationCatalogProvider",
    "MediaGenerationCatalogSource",
    "MediaGenerationNormalizationMetadataInput",
    "MediaNormalizationEntry",
    "MediaNormalizationValue",
    "ParsedGenerationModelRef",
    "find_capability_provider_by_id",
    "has_media_normalization_entry",
    "list_media_generation_provider_models",
    "normalize_optional_string",
    "parse_generation_model_ref",
    "resolve_capability_model_ref_for_providers",
    "resolve_capability_provider_model_only_ref",
    "synthesize_media_generation_catalog_entries",
    "unique_trimmed_strings",
]
