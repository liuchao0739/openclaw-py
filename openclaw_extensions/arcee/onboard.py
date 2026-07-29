from typing import Any

from .models import ARCEE_BASE_URL
from .provider_catalog import (
    OPENROUTER_BASE_URL,
    build_arcee_catalog_models,
    build_arcee_openrouter_catalog_models,
)

ARCEE_DEFAULT_MODEL_REF = "arcee/trinity-large-thinking"
ARCEE_OPENROUTER_DEFAULT_MODEL_REF = "arcee/trinity-large-thinking"


def _apply_provider_config(
    cfg: Any,
    *,
    base_url: str,
    catalog_models: list,
    primary_model_ref: str,
    alias: str,
) -> Any:
    if not isinstance(cfg, dict):
        cfg = {}
    providers = cfg.get("providers", {})
    if not isinstance(providers, dict):
        providers = {}
    providers["arcee"] = {
        "api": "openai-completions",
        "baseUrl": base_url,
    }
    models = cfg.get("models", {})
    if not isinstance(models, dict):
        models = {}
    for model in catalog_models:
        models[model["id"]] = model
    agents_cfg = cfg.get("agents", {})
    if not isinstance(agents_cfg, dict):
        agents_cfg = {}
    defaults_cfg = agents_cfg.get("defaults", {})
    if not isinstance(defaults_cfg, dict):
        defaults_cfg = {}
    agents_models = defaults_cfg.get("models", {})
    if not isinstance(agents_models, dict):
        agents_models = {}
    existing = agents_models.get(primary_model_ref, {})
    if not isinstance(existing, dict):
        existing = {}
    merged = dict(existing)
    merged.setdefault("alias", alias)
    agents_models[primary_model_ref] = merged
    defaults_cfg["models"] = agents_models
    defaults_cfg["model"] = primary_model_ref
    agents_cfg["defaults"] = defaults_cfg
    cfg["providers"] = providers
    cfg["models"] = models
    cfg["agents"] = agents_cfg
    return cfg


def apply_arcee_config(cfg: Any) -> Any:
    return _apply_provider_config(
        cfg,
        base_url=ARCEE_BASE_URL,
        catalog_models=build_arcee_catalog_models(),
        primary_model_ref=ARCEE_DEFAULT_MODEL_REF,
        alias="Arcee AI",
    )


def apply_arcee_openrouter_config(cfg: Any) -> Any:
    return _apply_provider_config(
        cfg,
        base_url=OPENROUTER_BASE_URL,
        catalog_models=build_arcee_openrouter_catalog_models(),
        primary_model_ref=ARCEE_OPENROUTER_DEFAULT_MODEL_REF,
        alias="Arcee AI (OpenRouter)",
    )
