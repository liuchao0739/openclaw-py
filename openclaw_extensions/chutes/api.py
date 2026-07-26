"""Public Chutes provider plugin API exports."""

from openclaw_extensions.chutes.model_discovery_env import (
    is_chutes_model_discovery_test_environment,
)
from openclaw_extensions.chutes.models import (
    CHUTES_BASE_URL,
    CHUTES_DEFAULT_MODEL_ID,
    CHUTES_DEFAULT_MODEL_REF,
    CHUTES_MODEL_CATALOG,
    build_chutes_model_definition,
    clear_chutes_model_cache_for_tests,
    discover_chutes_models,
)
from openclaw_extensions.chutes.oauth import login_chutes
from openclaw_extensions.chutes.onboard import (
    apply_chutes_api_key_config,
    apply_chutes_config,
    apply_chutes_provider_config,
)
from openclaw_extensions.chutes.provider_catalog import (
    build_chutes_provider,
    build_static_chutes_provider,
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
