from copy import deepcopy
from typing import TypedDict, List, Optional, Any


class ModelCost(TypedDict, total=False):
    input: float
    output: float
    cacheRead: float
    cacheWrite: float


class ModelCompat(TypedDict, total=False):
    supportsUsageInStreaming: bool
    supportsReasoningEffort: bool
    maxTokensField: str


class ModelDefinitionConfig(TypedDict, total=False):
    id: str
    name: str
    reasoning: bool
    input: List[str]
    contextWindow: int
    maxTokens: int
    cost: ModelCost
    compat: ModelCompat
    api: str


class ModelProviderConfig(TypedDict, total=False):
    providerId: str
    api: str
    baseUrl: str
    models: List[ModelDefinitionConfig]


MANIFEST: dict = {
    "id": "deepseek",
    "modelCatalog": {
        "providers": {
            "deepseek": {
                "baseUrl": "https://api.deepseek.com",
                "api": "openai-completions",
                "models": [
                    {
                        "id": "deepseek-v4-flash",
                        "name": "DeepSeek V4 Flash",
                        "reasoning": True,
                        "input": ["text"],
                        "contextWindow": 1000000,
                        "maxTokens": 384000,
                        "cost": {
                            "input": 0.14,
                            "output": 0.28,
                            "cacheRead": 0.028,
                            "cacheWrite": 0,
                        },
                        "compat": {
                            "supportsUsageInStreaming": True,
                            "supportsReasoningEffort": True,
                            "maxTokensField": "max_tokens",
                        },
                    },
                    {
                        "id": "deepseek-v4-pro",
                        "name": "DeepSeek V4 Pro",
                        "reasoning": True,
                        "input": ["text"],
                        "contextWindow": 1000000,
                        "maxTokens": 384000,
                        "cost": {
                            "input": 1.74,
                            "output": 3.48,
                            "cacheRead": 0.145,
                            "cacheWrite": 0,
                        },
                        "compat": {
                            "supportsUsageInStreaming": True,
                            "supportsReasoningEffort": True,
                            "maxTokensField": "max_tokens",
                        },
                    },
                    {
                        "id": "deepseek-chat",
                        "name": "DeepSeek Chat",
                        "input": ["text"],
                        "contextWindow": 131072,
                        "maxTokens": 8192,
                        "cost": {
                            "input": 0.28,
                            "output": 0.42,
                            "cacheRead": 0.028,
                            "cacheWrite": 0,
                        },
                        "compat": {
                            "supportsUsageInStreaming": True,
                            "maxTokensField": "max_tokens",
                        },
                    },
                    {
                        "id": "deepseek-reasoner",
                        "name": "DeepSeek Reasoner",
                        "reasoning": True,
                        "input": ["text"],
                        "contextWindow": 131072,
                        "maxTokens": 65536,
                        "cost": {
                            "input": 0.28,
                            "output": 0.42,
                            "cacheRead": 0.028,
                            "cacheWrite": 0,
                        },
                        "compat": {
                            "supportsUsageInStreaming": True,
                            "supportsReasoningEffort": False,
                            "maxTokensField": "max_tokens",
                        },
                    },
                ],
            },
        },
        "discovery": {
            "deepseek": "static",
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


_DEEPSEEK_MANIFEST_PROVIDER = _build_manifest_model_provider_config(
    "deepseek", MANIFEST["modelCatalog"]
)

DEEPSEEK_BASE_URL: str = _DEEPSEEK_MANIFEST_PROVIDER["baseUrl"]

DEEPSEEK_MODEL_CATALOG: List[ModelDefinitionConfig] = _DEEPSEEK_MANIFEST_PROVIDER["models"]


def build_deepseek_model_definition(model: ModelDefinitionConfig) -> ModelDefinitionConfig:
    merged: ModelDefinitionConfig = deepcopy(model)
    merged["api"] = "openai-completions"
    return merged


_V4_MODEL_IDS = {"deepseek-v4-flash", "deepseek-v4-pro"}


def is_deepseek_v4_model_id(model_id: str) -> bool:
    return model_id.lower() in _V4_MODEL_IDS


def is_deepseek_v4_model_ref(model: Any) -> bool:
    if not isinstance(model, dict):
        return False
    return (
        model.get("provider") == "deepseek"
        and isinstance(model.get("id"), str)
        and is_deepseek_v4_model_id(model["id"])
    )
