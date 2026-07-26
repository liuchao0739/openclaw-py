"""Arcee provider catalog builders for direct API and OpenRouter routing."""

from __future__ import annotations

import copy

from openclaw.packages.normalization_core import normalize_optional_string
from openclaw.plugin_sdk.provider_catalog_shared import ModelDefinitionConfig, ModelProviderConfig
from openclaw_extensions.arcee.models import (
    ARCEE_BASE_URL,
    ARCEE_MODEL_CATALOG,
    build_arcee_model_definition,
)

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
_OPENROUTER_LEGACY_BASE_URL = "https://openrouter.ai/v1"


def _normalize_base_url(base_url: str | None) -> str:
    normalized = normalize_optional_string(base_url)
    if not normalized:
        return ""
    return normalized.rstrip("/")


def normalize_arcee_open_router_base_url(base_url: str | None) -> str | None:
    normalized = _normalize_base_url(base_url)
    if not normalized:
        return None
    if normalized in (OPENROUTER_BASE_URL, _OPENROUTER_LEGACY_BASE_URL):
        return OPENROUTER_BASE_URL
    return None


def to_arcee_open_router_model_id(model_id: str) -> str:
    normalized = model_id.strip()
    if not normalized or normalized.startswith("arcee/"):
        return normalized
    return f"arcee/{normalized}"


def build_arcee_catalog_models() -> list[ModelDefinitionConfig]:
    return [build_arcee_model_definition(model) for model in ARCEE_MODEL_CATALOG]


def build_arcee_open_router_catalog_models() -> list[ModelDefinitionConfig]:
    return [
        {**copy.deepcopy(model), "id": to_arcee_open_router_model_id(model["id"])}
        for model in build_arcee_catalog_models()
    ]


def build_arcee_provider() -> ModelProviderConfig:
    return {
        "baseUrl": ARCEE_BASE_URL,
        "api": "openai-completions",
        "models": build_arcee_catalog_models(),
    }


def build_arcee_open_router_provider() -> ModelProviderConfig:
    return {
        "baseUrl": OPENROUTER_BASE_URL,
        "api": "openai-completions",
        "models": build_arcee_open_router_catalog_models(),
    }
