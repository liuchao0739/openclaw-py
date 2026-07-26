"""Cohere provider extension."""

from openclaw_extensions.cohere.models import (
    COHERE_BASE_URL,
    COHERE_MODEL_CATALOG,
    build_cohere_catalog_models,
    build_cohere_model_definition,
)
from openclaw_extensions.cohere.onboard import (
    COHERE_DEFAULT_MODEL_ID,
    COHERE_DEFAULT_MODEL_REF,
    apply_cohere_config,
)
from openclaw_extensions.cohere.provider_catalog import build_cohere_provider
from openclaw_extensions.cohere.stream import create_cohere_completions_wrapper

__all__ = [
    "COHERE_BASE_URL",
    "COHERE_DEFAULT_MODEL_ID",
    "COHERE_DEFAULT_MODEL_REF",
    "COHERE_MODEL_CATALOG",
    "apply_cohere_config",
    "build_cohere_catalog_models",
    "build_cohere_model_definition",
    "build_cohere_provider",
    "create_cohere_completions_wrapper",
]
