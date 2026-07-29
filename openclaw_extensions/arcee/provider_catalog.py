import re
from typing import List, Optional

from .models import (
    ARCEE_BASE_URL,
    ARCEE_MODEL_CATALOG,
    ModelDefinitionConfig,
    ModelProviderConfig,
    build_arcee_model_definition,
)

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_LEGACY_BASE_URL = "https://openrouter.ai/v1"


def _normalize_base_url(base_url: Optional[str]) -> str:
    return re.sub(r"/+$", "", (base_url or "").strip())


def normalize_arcee_openrouter_base_url(base_url: Optional[str]) -> Optional[str]:
    normalized = _normalize_base_url(base_url)
    if not normalized:
        return None
    if normalized == OPENROUTER_BASE_URL or normalized == OPENROUTER_LEGACY_BASE_URL:
        return OPENROUTER_BASE_URL
    return None


def to_arcee_openrouter_model_id(model_id: str) -> str:
    normalized = (model_id or "").strip()
    if not normalized or normalized.startswith("arcee/"):
        return normalized
    return f"arcee/{normalized}"


def build_arcee_catalog_models() -> List[ModelDefinitionConfig]:
    return [build_arcee_model_definition(model) for model in ARCEE_MODEL_CATALOG]


def build_arcee_openrouter_catalog_models() -> List[ModelDefinitionConfig]:
    models: List[ModelDefinitionConfig] = []
    for model in build_arcee_catalog_models():
        patched = dict(model)
        patched["id"] = to_arcee_openrouter_model_id(model["id"])
        models.append(patched)
    return models


def build_arcee_provider() -> ModelProviderConfig:
    return {
        "baseUrl": ARCEE_BASE_URL,
        "api": "openai-completions",
        "models": build_arcee_catalog_models(),
    }


def build_arcee_openrouter_provider() -> ModelProviderConfig:
    return {
        "baseUrl": OPENROUTER_BASE_URL,
        "api": "openai-completions",
        "models": build_arcee_openrouter_catalog_models(),
    }
