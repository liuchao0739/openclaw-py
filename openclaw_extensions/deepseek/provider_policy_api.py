"""DeepSeek provider policy surface."""

from __future__ import annotations

import math
from typing import Any

from openclaw.packages.normalization_core import is_record
from openclaw.plugin_sdk.provider_catalog_shared import ModelProviderConfig
from openclaw_extensions.deepseek.models import DEEPSEEK_MODEL_CATALOG
from openclaw_extensions.deepseek.thinking import resolve_deep_seek_v4_thinking_profile


def _build_catalog_index() -> dict[str, dict[str, Any]]:
    return {str(model["id"]): model for model in DEEPSEEK_MODEL_CATALOG}


def _is_positive_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and math.isfinite(value) and value > 0


def _has_cost_values(cost: Any) -> bool:
    if not is_record(cost):
        return False
    return any(isinstance(cost.get(key), (int, float)) for key in ("input", "output", "cacheRead", "cacheWrite"))


def normalize_config(params: dict[str, Any]) -> ModelProviderConfig:
    """Hydrate missing contextWindow, cost, and maxTokens from the bundled catalog."""
    provider_config = params["providerConfig"]
    models = provider_config.get("models")
    if not isinstance(models, list) or not models:
        return provider_config

    catalog = _build_catalog_index()
    mutated = False
    next_models: list[Any] = []

    for model in models:
        if not is_record(model):
            next_models.append(model)
            continue

        catalog_entry = catalog.get(str(model.get("id", "")))
        if catalog_entry is None:
            next_models.append(model)
            continue

        patched: dict[str, Any] = {}
        model_mutated = False

        if not _is_positive_number(model.get("contextWindow")) and _is_positive_number(
            catalog_entry.get("contextWindow")
        ):
            patched["contextWindow"] = catalog_entry["contextWindow"]
            model_mutated = True

        if not _is_positive_number(model.get("maxTokens")) and _is_positive_number(
            catalog_entry.get("maxTokens")
        ):
            patched["maxTokens"] = catalog_entry["maxTokens"]
            model_mutated = True

        if not _has_cost_values(model.get("cost")) and _has_cost_values(catalog_entry.get("cost")):
            patched["cost"] = catalog_entry["cost"]
            model_mutated = True

        if not model_mutated:
            next_models.append(model)
            continue

        mutated = True
        next_models.append({**model, **patched})

    if not mutated:
        return provider_config

    return {**provider_config, "models": next_models}


def resolve_thinking_profile(params: dict[str, Any]) -> dict[str, Any] | None:
    if params["provider"].strip().lower() == "deepseek":
        return resolve_deep_seek_v4_thinking_profile(params["modelId"])
    return None
