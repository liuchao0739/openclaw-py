from typing import Any

from .provider_catalog import (
    build_fireworks_catalog_models,
    build_fireworks_provider,
    FIREWORKS_DEFAULT_MODEL_ID,
)

FIREWORKS_DEFAULT_MODEL_REF = f"fireworks/{FIREWORKS_DEFAULT_MODEL_ID}"


def _build_default_models_preset_appliers(primary_model_ref: str):
    def resolve_params(cfg: Any) -> dict:
        default_provider = build_fireworks_provider()
        return {
            "providerId": "fireworks",
            "api": default_provider.get("api", "openai-completions"),
            "baseUrl": default_provider.get("baseUrl", ""),
            "defaultModels": build_fireworks_catalog_models(),
            "defaultModelId": FIREWORKS_DEFAULT_MODEL_ID,
            "aliases": [{"modelRef": FIREWORKS_DEFAULT_MODEL_REF, "alias": "Kimi K2.5 Turbo"}],
        }

    def apply_config(cfg: Any) -> Any:
        params = resolve_params(cfg)
        provider_id = params["providerId"]
        default_model_id = params["defaultModelId"]
        providers = cfg.get("providers", {}) if isinstance(cfg, dict) else {}
        providers[provider_id] = {
            "api": params["api"],
            "baseUrl": params["baseUrl"],
        }
        models = cfg.get("models", {}) if isinstance(cfg, dict) else {}
        for model in params["defaultModels"]:
            models[model["id"]] = model
        default_model_ref = f"{provider_id}/{default_model_id}"
        cfg.setdefault("defaults", {})["model"] = default_model_ref
        if isinstance(cfg, dict):
            cfg["providers"] = providers
            cfg["models"] = models
        return cfg

    return {"applyConfig": apply_config, "resolveParams": resolve_params}


_fireworks_preset_appliers = _build_default_models_preset_appliers(
    primary_model_ref=FIREWORKS_DEFAULT_MODEL_REF,
)


def apply_fireworks_config(cfg: Any) -> Any:
    return _fireworks_preset_appliers["applyConfig"](cfg)
