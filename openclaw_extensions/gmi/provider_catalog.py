"""GMI provider model/runtime integration."""

from __future__ import annotations

from openclaw.plugin_sdk.provider_catalog_shared import ModelProviderConfig
from openclaw_extensions.gmi.models import (
    GMI_BASE_URL,
    GMI_MODEL_CATALOG,
    build_gmi_model_definition,
)


def build_gmi_provider() -> ModelProviderConfig:
    return {
        "baseUrl": GMI_BASE_URL,
        "api": "openai-completions",
        "models": [build_gmi_model_definition(model) for model in GMI_MODEL_CATALOG],
    }
