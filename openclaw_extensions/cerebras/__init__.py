"""Cerebras provider extension."""

from openclaw_extensions.cerebras.api import (
    CEREBRAS_BASE_URL,
    CEREBRAS_DEFAULT_MODEL_REF,
    CEREBRAS_MODEL_CATALOG,
    apply_cerebras_config,
    build_cerebras_catalog_models,
    build_cerebras_model_definition,
    build_cerebras_provider,
)

__all__ = [
    "CEREBRAS_BASE_URL",
    "CEREBRAS_DEFAULT_MODEL_REF",
    "CEREBRAS_MODEL_CATALOG",
    "apply_cerebras_config",
    "build_cerebras_catalog_models",
    "build_cerebras_model_definition",
    "build_cerebras_provider",
]
