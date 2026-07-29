from typing import Any

from .models import (
    DEEPSEEK_BASE_URL,
    DEEPSEEK_MODEL_CATALOG,
    build_deepseek_model_definition,
)
from .provider_catalog import build_deepseek_provider

DEEPSEEK_DEFAULT_MODEL_REF = "deepseek/deepseek-v4-flash"
DEEPSEEK_DEFAULT_MODEL_ID = "deepseek-v4-flash"


def _apply_deepseek_provider_config(cfg: Any) -> Any:
    if not isinstance(cfg, dict):
        cfg = {}
    providers = cfg.get("providers", {})
    provider = build_deepseek_provider()
    providers["deepseek"] = {
        "api": provider.get("api", "openai-completions"),
        "baseUrl": provider.get("baseUrl", DEEPSEEK_BASE_URL),
    }

    models = cfg.get("models", {})
    agents_defaults_models = cfg.get("agents", {}).get("defaults", {}).get("models", {}) if isinstance(cfg.get("agents"), dict) else {}
    existing = agents_defaults_models.get(DEEPSEEK_DEFAULT_MODEL_REF, {}) if isinstance(agents_defaults_models, dict) else {}
    merged = dict(existing)
    merged.setdefault("alias", "DeepSeek")
    agents_defaults_models[DEEPSEEK_DEFAULT_MODEL_REF] = merged

    for model in DEEPSEEK_MODEL_CATALOG:
        models[model["id"]] = build_deepseek_model_definition(model)

    cfg["providers"] = providers
    cfg["models"] = models
    agents_cfg = cfg.get("agents", {})
    if not isinstance(agents_cfg, dict):
        agents_cfg = {}
    defaults_cfg = agents_cfg.get("defaults", {})
    if not isinstance(defaults_cfg, dict):
        defaults_cfg = {}
    defaults_cfg["models"] = agents_defaults_models
    agents_cfg["defaults"] = defaults_cfg
    cfg["agents"] = agents_cfg
    return cfg


def _apply_agent_default_model_primary(cfg: Any, model_ref: str) -> Any:
    if not isinstance(cfg, dict):
        cfg = {}
    agents_cfg = cfg.get("agents", {})
    if not isinstance(agents_cfg, dict):
        agents_cfg = {}
    defaults_cfg = agents_cfg.get("defaults", {})
    if not isinstance(defaults_cfg, dict):
        defaults_cfg = {}
    defaults_cfg["model"] = model_ref
    agents_cfg["defaults"] = defaults_cfg
    cfg["agents"] = agents_cfg
    return cfg


def apply_deepseek_config(cfg: Any) -> Any:
    cfg = _apply_deepseek_provider_config(cfg)
    cfg = _apply_agent_default_model_primary(cfg, DEEPSEEK_DEFAULT_MODEL_REF)
    return cfg
