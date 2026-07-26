"""Provider catalog helpers normalize manifest model catalogs for provider plugins."""

from __future__ import annotations

from typing import Any

from openclaw.packages.normalization_core import is_record

ModelDefinitionConfig = dict[str, Any]
ModelProviderConfig = dict[str, Any]

__all__ = [
    "ModelDefinitionConfig",
    "ModelProviderConfig",
    "build_manifest_model_provider_config",
]


def _count_raw_manifest_catalog_models(catalog: Any) -> int | None:
    if not is_record(catalog):
        return None
    models = catalog.get("models")
    return len(models) if isinstance(models, list) else None


def _clone_manifest_catalog_tiered_cost(tier: dict[str, Any]) -> dict[str, Any]:
    range_value = tier.get("range")
    if not isinstance(range_value, list) or not range_value:
        raise ValueError("invalid tiered pricing range")
    normalized_range = (
        [range_value[0]] if len(range_value) == 1 else [range_value[0], range_value[1]]
    )
    return {
        "input": tier.get("input"),
        "output": tier.get("output"),
        "cacheRead": tier.get("cacheRead"),
        "cacheWrite": tier.get("cacheWrite"),
        "range": normalized_range,
    }


def _clone_manifest_catalog_cost(cost: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {
        "input": cost.get("input", 0),
        "output": cost.get("output", 0),
        "cacheRead": cost.get("cacheRead", 0),
        "cacheWrite": cost.get("cacheWrite", 0),
    }
    tiered = cost.get("tieredPricing")
    if isinstance(tiered, list):
        cloned = [_clone_manifest_catalog_tiered_cost(tier) for tier in tiered if is_record(tier)]
        if cloned:
            result["tieredPricing"] = cloned
    return result


def _build_manifest_catalog_model_input(model: dict[str, Any]) -> list[str]:
    raw_input = model.get("input")
    if not isinstance(raw_input, list):
        return ["text"]
    if "document" in raw_input:
        model_id = model.get("id", "<unknown>")
        raise ValueError(
            f"Manifest modelCatalog row {model_id} uses unsupported runtime input document"
        )
    normalized = [item for item in raw_input if item in ("text", "image", "audio", "video")]
    return normalized or ["text"]


def _clone_manifest_catalog_media_input(media_input: Any) -> dict[str, Any] | None:
    if not is_record(media_input):
        return None
    image = media_input.get("image")
    if not is_record(image):
        return None
    return {"image": dict(image)}


def _build_manifest_catalog_model(
    provider_id: str,
    model: dict[str, Any],
) -> ModelDefinitionConfig:
    model_id = model.get("id")
    if model.get("contextWindow") is None:
        raise ValueError(f"Manifest modelCatalog row {model_id} is missing contextWindow")
    if model.get("maxTokens") is None:
        raise ValueError(f"Manifest modelCatalog row {model_id} is missing maxTokens")

    id_value = str(model_id) if model_id is not None else ""
    result: ModelDefinitionConfig = {
        "id": id_value,
        "name": model.get("name") or id_value,
        "reasoning": model.get("reasoning", False),
        "input": _build_manifest_catalog_model_input(model),
        "cost": _clone_manifest_catalog_cost(
            model.get("cost") if is_record(model.get("cost")) else {}
        ),
        "contextWindow": model["contextWindow"],
        "maxTokens": model["maxTokens"],
    }
    if model.get("api"):
        result["api"] = model["api"]
    if model.get("baseUrl"):
        result["baseUrl"] = model["baseUrl"]
    if model.get("contextTokens") is not None:
        result["contextTokens"] = model["contextTokens"]
    if is_record(model.get("headers")):
        result["headers"] = dict(model["headers"])
    if is_record(model.get("compat")):
        result["compat"] = dict(model["compat"])
    media = _clone_manifest_catalog_media_input(model.get("mediaInput"))
    if media:
        result["mediaInput"] = media
    return result


def build_manifest_model_provider_config(
    *,
    provider_id: str,
    catalog: Any,
) -> ModelProviderConfig:
    """Convert a plugin manifest modelCatalog provider into runtime provider config."""
    if not is_record(catalog):
        raise ValueError(f"Missing modelCatalog.providers.{provider_id}")
    base_url = catalog.get("baseUrl")
    if not base_url:
        raise ValueError(f"Missing modelCatalog.providers.{provider_id}.baseUrl")

    models_raw = catalog.get("models")
    if not isinstance(models_raw, list):
        raise TypeError(f"Invalid modelCatalog.providers.{provider_id}.models")

    models = [
        _build_manifest_catalog_model(provider_id, model)
        for model in models_raw
        if is_record(model)
    ]
    raw_model_count = _count_raw_manifest_catalog_models(catalog)
    if raw_model_count is not None and raw_model_count != len(models):
        raise ValueError(f"Invalid modelCatalog.providers.{provider_id}.models")

    result: ModelProviderConfig = {
        "baseUrl": base_url,
        "models": models,
    }
    if catalog.get("api"):
        result["api"] = catalog["api"]
    if is_record(catalog.get("headers")):
        result["headers"] = dict(catalog["headers"])
    return result
