"""Chutes provider extension."""

from openclaw_extensions.chutes.api import (
    CHUTES_BASE_URL,
    CHUTES_DEFAULT_MODEL_ID,
    CHUTES_DEFAULT_MODEL_REF,
    CHUTES_MODEL_CATALOG,
    apply_chutes_api_key_config,
    apply_chutes_config,
    apply_chutes_provider_config,
    build_chutes_model_definition,
    build_chutes_provider,
    build_static_chutes_provider,
    clear_chutes_model_cache_for_tests,
    discover_chutes_models,
    is_chutes_model_discovery_test_environment,
    login_chutes,
)

__all__ = [
    "CHUTES_BASE_URL",
    "CHUTES_DEFAULT_MODEL_ID",
    "CHUTES_DEFAULT_MODEL_REF",
    "CHUTES_MODEL_CATALOG",
    "apply_chutes_api_key_config",
    "apply_chutes_config",
    "apply_chutes_provider_config",
    "build_chutes_model_definition",
    "build_chutes_provider",
    "build_static_chutes_provider",
    "clear_chutes_model_cache_for_tests",
    "discover_chutes_models",
    "is_chutes_model_discovery_test_environment",
    "login_chutes",
]
