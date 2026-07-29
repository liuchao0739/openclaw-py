from copy import deepcopy
from typing import Any, Optional

from .models import DEEPSEEK_MODEL_CATALOG, ModelDefinitionConfig
from .thinking_policy import resolve_deepseek_v4_thinking_profile, ThinkingProfile


def _build_catalog_index() -> dict:
    index = {}
    for model in DEEPSEEK_MODEL_CATALOG:
        index[model["id"]] = model
    return index


def _is_positive_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and value == value and value > 0


def _has_cost_values(cost: Any) -> bool:
    if not isinstance(cost, dict):
        return False
    return (
        isinstance(cost.get("input"), (int, float))
        or isinstance(cost.get("output"), (int, float))
        or isinstance(cost.get("cacheRead"), (int, float))
        or isinstance(cost.get("cacheWrite"), (int, float))
    )


def normalize_config(params: dict) -> dict:
    provider_config = params.get("providerConfig", {})
    if not isinstance(provider_config, dict):
        return provider_config
    models = provider_config.get("models")
    if not isinstance(models, list) or len(models) == 0:
        return provider_config

    catalog = _build_catalog_index()
    mutated = False

    next_models = []
    for model in models:
        if not isinstance(model, dict):
            next_models.append(model)
            continue
        raw_id = model.get("id")
        catalog_entry = catalog.get(raw_id) if isinstance(raw_id, str) else None
        if not catalog_entry:
            next_models.append(model)
            continue

        model_mutated = False
        patched: dict = {}

        if not _is_positive_number(model.get("contextWindow")) and _is_positive_number(catalog_entry.get("contextWindow")):
            patched["contextWindow"] = catalog_entry["contextWindow"]
            model_mutated = True

        if not _is_positive_number(model.get("maxTokens")) and _is_positive_number(catalog_entry.get("maxTokens")):
            patched["maxTokens"] = catalog_entry["maxTokens"]
            model_mutated = True

        if not _has_cost_values(model.get("cost")) and _has_cost_values(catalog_entry.get("cost")):
            patched["cost"] = deepcopy(catalog_entry["cost"])
            model_mutated = True

        if not model_mutated:
            next_models.append(model)
            continue

        mutated = True
        merged = deepcopy(model)
        merged.update(patched)
        next_models.append(merged)

    if not mutated:
        return provider_config

    result = deepcopy(provider_config)
    result["models"] = next_models
    return result


def resolve_thinking_profile(params: dict) -> Optional[ThinkingProfile]:
    provider = str(params.get("provider", "")).strip().lower()
    if provider != "deepseek":
        return None
    model_id = params.get("modelId", "")
    if not isinstance(model_id, str):
        return None
    return resolve_deepseek_v4_thinking_profile(model_id)
