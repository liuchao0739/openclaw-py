"""Public barrel for model catalog normalization, ids, refs, and types.

Mirrors packages/model-catalog-core/src/index.ts.
"""

from __future__ import annotations

from .configured_model_refs import (
    AGENT_MODEL_CONFIG_KEYS,
    ConfiguredModelRef,
    collect_configured_model_ref_values,
    collect_configured_model_refs,
    extract_provider_from_model_ref,
)
from .model_catalog_normalize import (
    normalize_model_catalog,
    normalize_model_catalog_provider_rows,
    normalize_model_catalog_rows,
)
from .model_catalog_refs import (
    build_model_catalog_merge_key,
    build_model_catalog_ref,
    normalize_model_catalog_provider_id,
)
from .model_catalog_types import (
    MODEL_CATALOG_APIS,
    MODEL_CATALOG_THINKING_FORMATS,
    is_model_catalog_thinking_format,
)
from .provider_id import (
    find_normalized_provider_key,
    find_normalized_provider_value,
    normalize_lowercase_string_or_empty,
    normalize_provider_id,
    normalize_provider_id_for_auth,
)
from .provider_model_id_normalization import (
    ManifestModelIdNormalizationProvider,
    ManifestModelIdNormalizationRecord,
    collect_manifest_model_id_normalization_policies,
    get_current_manifest_model_id_normalization_policies,
    normalize_built_in_provider_model_id,
    normalize_configured_provider_catalog_model_id,
    normalize_configured_provider_catalog_model_ref,
    normalize_provider_model_id_with_policies,
    normalize_static_provider_model_id_with_policies,
    set_current_manifest_model_id_normalization_records,
    strip_self_provider_model_prefix,
)
from .provider_model_id_normalize import (
    normalize_antigravity_preview_model_id,
    normalize_google_preview_model_id,
    normalize_together_model_id,
)

__all__ = [
    "AGENT_MODEL_CONFIG_KEYS",
    "MODEL_CATALOG_APIS",
    "MODEL_CATALOG_THINKING_FORMATS",
    "ConfiguredModelRef",
    "ManifestModelIdNormalizationProvider",
    "ManifestModelIdNormalizationRecord",
    "build_model_catalog_merge_key",
    "build_model_catalog_ref",
    "collect_configured_model_ref_values",
    "collect_configured_model_refs",
    "collect_manifest_model_id_normalization_policies",
    "extract_provider_from_model_ref",
    "find_normalized_provider_key",
    "find_normalized_provider_value",
    "get_current_manifest_model_id_normalization_policies",
    "is_model_catalog_thinking_format",
    "normalize_antigravity_preview_model_id",
    "normalize_built_in_provider_model_id",
    "normalize_configured_provider_catalog_model_id",
    "normalize_configured_provider_catalog_model_ref",
    "normalize_google_preview_model_id",
    "normalize_lowercase_string_or_empty",
    "normalize_model_catalog",
    "normalize_model_catalog_provider_id",
    "normalize_model_catalog_provider_rows",
    "normalize_model_catalog_rows",
    "normalize_provider_id",
    "normalize_provider_id_for_auth",
    "normalize_provider_model_id_with_policies",
    "normalize_static_provider_model_id_with_policies",
    "normalize_together_model_id",
    "set_current_manifest_model_id_normalization_records",
    "strip_self_provider_model_prefix",
]
