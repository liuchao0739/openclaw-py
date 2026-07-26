"""DeepSeek provider extension."""

from openclaw_extensions.deepseek.api import (
    DEEPSEEK_BASE_URL,
    DEEPSEEK_MODEL_CATALOG,
    build_deep_seek_model_definition,
    build_deep_seek_provider,
    create_deep_seek_v4_thinking_wrapper,
)
from openclaw_extensions.deepseek.models import is_deep_seek_v4_model_id, is_deep_seek_v4_model_ref
from openclaw_extensions.deepseek.onboard import DEEPSEEK_DEFAULT_MODEL_REF, apply_deep_seek_config
from openclaw_extensions.deepseek.provider_policy_api import (
    normalize_config,
    resolve_thinking_profile,
)
from openclaw_extensions.deepseek.thinking import resolve_deep_seek_v4_thinking_profile

__all__ = [
    "DEEPSEEK_BASE_URL",
    "DEEPSEEK_DEFAULT_MODEL_REF",
    "DEEPSEEK_MODEL_CATALOG",
    "apply_deep_seek_config",
    "build_deep_seek_model_definition",
    "build_deep_seek_provider",
    "create_deep_seek_v4_thinking_wrapper",
    "is_deep_seek_v4_model_id",
    "is_deep_seek_v4_model_ref",
    "normalize_config",
    "resolve_deep_seek_v4_thinking_profile",
    "resolve_thinking_profile",
]
