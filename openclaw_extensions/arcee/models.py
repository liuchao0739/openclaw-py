from copy import deepcopy
from typing import List, TypedDict


class ModelCost(TypedDict, total=False):
    input: float
    output: float
    cacheRead: float
    cacheWrite: float


class ModelCompat(TypedDict, total=False):
    supportsTools: bool
    supportsReasoningEffort: bool


class ModelDefinitionConfig(TypedDict, total=False):
    id: str
    name: str
    api: str
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


ARCEE_BASE_URL = "https://api.arcee.ai/api/v1"

ARCEE_MODEL_CATALOG: List[ModelDefinitionConfig] = [
    {
        "id": "trinity-mini",
        "name": "Trinity Mini 26B",
        "reasoning": False,
        "input": ["text"],
        "contextWindow": 131072,
        "maxTokens": 80000,
        "cost": {
            "input": 0.045,
            "output": 0.15,
            "cacheRead": 0.045,
            "cacheWrite": 0.045,
        },
    },
    {
        "id": "trinity-large-preview",
        "name": "Trinity Large Preview",
        "reasoning": False,
        "input": ["text"],
        "contextWindow": 131072,
        "maxTokens": 16384,
        "cost": {
            "input": 0.25,
            "output": 1,
            "cacheRead": 0.25,
            "cacheWrite": 0.25,
        },
    },
    {
        "id": "trinity-large-thinking",
        "name": "Trinity Large Thinking",
        "reasoning": True,
        "input": ["text"],
        "contextWindow": 262144,
        "maxTokens": 80000,
        "cost": {
            "input": 0.25,
            "output": 0.9,
            "cacheRead": 0.25,
            "cacheWrite": 0.25,
        },
        "compat": {
            "supportsTools": False,
            "supportsReasoningEffort": False,
        },
    },
]


def build_arcee_model_definition(model: ModelDefinitionConfig) -> ModelDefinitionConfig:
    result: ModelDefinitionConfig = {
        "id": model["id"],
        "name": model["name"],
        "api": "openai-completions",
        "reasoning": model.get("reasoning", False),
        "input": model["input"],
        "cost": model["cost"],
        "contextWindow": model["contextWindow"],
        "maxTokens": model["maxTokens"],
    }
    if "compat" in model:
        result["compat"] = deepcopy(model["compat"])
    return result
