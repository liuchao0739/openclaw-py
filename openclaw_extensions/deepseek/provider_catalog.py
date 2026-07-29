from typing import List

from .models import (
    DEEPSEEK_BASE_URL,
    DEEPSEEK_MODEL_CATALOG,
    build_deepseek_model_definition,
    ModelProviderConfig,
    ModelDefinitionConfig,
)


def build_deepseek_provider() -> ModelProviderConfig:
    models: List[ModelDefinitionConfig] = [
        build_deepseek_model_definition(model) for model in DEEPSEEK_MODEL_CATALOG
    ]
    return {
        "baseUrl": DEEPSEEK_BASE_URL,
        "api": "openai-completions",
        "models": models,
    }
