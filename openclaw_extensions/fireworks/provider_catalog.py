from copy import deepcopy
from typing import TypedDict, List, Optional, Any


class ModelCost(TypedDict, total=False):
    input: float
    output: float
    cacheRead: float
    cacheWrite: float


class ModelCompat(TypedDict, total=False):
    unsupportedToolSchemaKeywords: List[str]


class ModelDefinitionConfig(TypedDict, total=False):
    id: str
    name: str
    reasoning: bool
    input: List[str]
    contextWindow: int
    maxTokens: int
    cost: ModelCost
    compat: ModelCompat


class ModelProviderConfig(TypedDict, total=False):
    providerId: str
    api: str
    baseUrl: str
    models: List[ModelDefinitionConfig]


MANIFEST: dict = {
    "id": "fireworks",
    "modelCatalog": {
        "providers": {
            "fireworks": {
                "baseUrl": "https://api.fireworks.ai/inference/v1",
                "api": "openai-completions",
                "models": [
                    {
                        "id": "accounts/fireworks/models/kimi-k2p6",
                        "name": "Kimi K2.6",
                        "reasoning": False,
                        "input": ["text", "image"],
                        "contextWindow": 262144,
                        "maxTokens": 262144,
                        "cost": {
                            "input": 0.95,
                            "output": 4,
                            "cacheRead": 0,
                            "cacheWrite": 0,
                        },
                    },
                    {
                        "id": "accounts/fireworks/routers/kimi-k2p5-turbo",
                        "name": "Kimi K2.5 Turbo (Fire Pass)",
                        "reasoning": False,
                        "input": ["text", "image"],
                        "contextWindow": 256000,
                        "maxTokens": 256000,
                        "compat": {
                            "unsupportedToolSchemaKeywords": ["not"],
                        },
                        "cost": {
                            "input": 0,
                            "output": 0,
                            "cacheRead": 0,
                            "cacheWrite": 0,
                        },
                    },
                ],
            },
        },
        "discovery": {
            "fireworks": "static",
        },
    },
}


def _build_manifest_model_provider_config(provider_id: str, catalog: dict) -> ModelProviderConfig:
    provider_catalog = catalog["providers"][provider_id]
    return {
        "providerId": provider_id,
        "api": provider_catalog.get("api", "openai-completions"),
        "baseUrl": provider_catalog.get("baseUrl", ""),
        "models": provider_catalog.get("models", []),
    }


_FIREWORKS_MANIFEST_PROVIDER = _build_manifest_model_provider_config(
    "fireworks", MANIFEST["modelCatalog"]
)

FIREWORKS_BASE_URL: str = _FIREWORKS_MANIFEST_PROVIDER["baseUrl"]
FIREWORKS_DEFAULT_MODEL_ID: str = "accounts/fireworks/routers/kimi-k2p5-turbo"


def _require_fireworks_manifest_model(model_id: str) -> ModelDefinitionConfig:
    for entry in _FIREWORKS_MANIFEST_PROVIDER["models"]:
        if entry["id"] == model_id:
            return entry
    raise ValueError(f"Missing Fireworks modelCatalog row {model_id}")


_FIREWORKS_DEFAULT_MODEL = _require_fireworks_manifest_model(FIREWORKS_DEFAULT_MODEL_ID)

FIREWORKS_DEFAULT_CONTEXT_WINDOW: int = _FIREWORKS_DEFAULT_MODEL["contextWindow"]
FIREWORKS_DEFAULT_MAX_TOKENS: int = _FIREWORKS_DEFAULT_MODEL["maxTokens"]


def is_fireworks_catalog_model_id(model_id: str) -> bool:
    return any(model["id"] == model_id for model in _FIREWORKS_MANIFEST_PROVIDER["models"])


def build_fireworks_catalog_models() -> List[ModelDefinitionConfig]:
    return [deepcopy(model) for model in _FIREWORKS_MANIFEST_PROVIDER["models"]]


def build_fireworks_provider() -> ModelProviderConfig:
    return _build_manifest_model_provider_config(
        "fireworks", MANIFEST["modelCatalog"]
    )
