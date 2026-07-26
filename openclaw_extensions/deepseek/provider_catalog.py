"""DeepSeek provider model/runtime integration."""

from __future__ import annotations

from openclaw.plugin_sdk.provider_catalog_shared import ModelProviderConfig
from openclaw_extensions.deepseek.models import (
    DEEPSEEK_BASE_URL,
    DEEPSEEK_MODEL_CATALOG,
    build_deep_seek_model_definition,
)


def build_deep_seek_provider() -> ModelProviderConfig:
    return {
        "baseUrl": DEEPSEEK_BASE_URL,
        "api": "openai-completions",
        "models": [build_deep_seek_model_definition(model) for model in DEEPSEEK_MODEL_CATALOG],
    }
