"""Fireworks provider extension."""

from openclaw_extensions.fireworks.model_id import is_fireworks_kimi_model_id
from openclaw_extensions.fireworks.onboard import (
    FIREWORKS_DEFAULT_MODEL_REF,
    apply_fireworks_config,
)
from openclaw_extensions.fireworks.provider_catalog import (
    FIREWORKS_BASE_URL,
    FIREWORKS_DEFAULT_CONTEXT_WINDOW,
    FIREWORKS_DEFAULT_MAX_TOKENS,
    FIREWORKS_DEFAULT_MODEL_ID,
    build_fireworks_catalog_models,
    build_fireworks_provider,
    is_fireworks_catalog_model_id,
)
from openclaw_extensions.fireworks.provider_policy_api import resolve_thinking_profile
from openclaw_extensions.fireworks.stream import (
    create_fireworks_kimi_thinking_disabled_wrapper,
    wrap_fireworks_provider_stream,
)
from openclaw_extensions.fireworks.thinking_policy import resolve_fireworks_thinking_profile

__all__ = [
    "FIREWORKS_BASE_URL",
    "FIREWORKS_DEFAULT_CONTEXT_WINDOW",
    "FIREWORKS_DEFAULT_MAX_TOKENS",
    "FIREWORKS_DEFAULT_MODEL_ID",
    "FIREWORKS_DEFAULT_MODEL_REF",
    "apply_fireworks_config",
    "build_fireworks_catalog_models",
    "build_fireworks_provider",
    "create_fireworks_kimi_thinking_disabled_wrapper",
    "is_fireworks_catalog_model_id",
    "is_fireworks_kimi_model_id",
    "resolve_fireworks_thinking_profile",
    "resolve_thinking_profile",
    "wrap_fireworks_provider_stream",
]
