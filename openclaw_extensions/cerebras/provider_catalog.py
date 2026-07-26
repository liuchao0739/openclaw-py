"""Cerebras model provider builder."""

from __future__ import annotations

from openclaw.plugin_sdk.provider_catalog_shared import ModelProviderConfig
from openclaw_extensions.cerebras.models import CEREBRAS_BASE_URL, build_cerebras_catalog_models


def build_cerebras_provider() -> ModelProviderConfig:
    return {
        "baseUrl": CEREBRAS_BASE_URL,
        "api": "openai-completions",
        "models": build_cerebras_catalog_models(),
    }
