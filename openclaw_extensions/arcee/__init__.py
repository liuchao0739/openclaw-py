"""Arcee AI provider extension."""

from openclaw_extensions.arcee.api import (
    ARCEE_BASE_URL,
    ARCEE_DEFAULT_MODEL_REF,
    ARCEE_MODEL_CATALOG,
    ARCEE_OPENROUTER_DEFAULT_MODEL_REF,
    OPENROUTER_BASE_URL,
    apply_arcee_config,
    apply_arcee_open_router_config,
    build_arcee_catalog_models,
    build_arcee_model_definition,
    build_arcee_open_router_catalog_models,
    build_arcee_open_router_provider,
    build_arcee_provider,
    normalize_arcee_open_router_base_url,
    to_arcee_open_router_model_id,
)

__all__ = [
    "ARCEE_BASE_URL",
    "ARCEE_DEFAULT_MODEL_REF",
    "ARCEE_MODEL_CATALOG",
    "ARCEE_OPENROUTER_DEFAULT_MODEL_REF",
    "OPENROUTER_BASE_URL",
    "apply_arcee_config",
    "apply_arcee_open_router_config",
    "build_arcee_catalog_models",
    "build_arcee_model_definition",
    "build_arcee_open_router_catalog_models",
    "build_arcee_open_router_provider",
    "build_arcee_provider",
    "normalize_arcee_open_router_base_url",
    "to_arcee_open_router_model_id",
]
