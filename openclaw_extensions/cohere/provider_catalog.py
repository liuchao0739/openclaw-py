"""Cohere provider model/runtime integration."""

from __future__ import annotations

from openclaw.plugin_sdk.provider_catalog_shared import ModelProviderConfig
from openclaw_extensions.cohere.models import COHERE_BASE_URL, build_cohere_catalog_models


def build_cohere_provider() -> ModelProviderConfig:
    return {
        "baseUrl": COHERE_BASE_URL,
        "api": "openai-completions",
        "models": build_cohere_catalog_models(),
    }
