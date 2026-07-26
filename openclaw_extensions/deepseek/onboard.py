"""DeepSeek setup module handles plugin onboarding behavior."""

from __future__ import annotations

from openclaw.packages.normalization_core import is_record
from openclaw.plugin_sdk.provider_onboard import (
    OpenClawConfig,
    apply_agent_default_model_primary,
    apply_provider_config_with_model_catalog,
)
from openclaw_extensions.deepseek.models import (
    DEEPSEEK_BASE_URL,
    DEEPSEEK_MODEL_CATALOG,
    build_deep_seek_model_definition,
)

DEEPSEEK_DEFAULT_MODEL_REF = "deepseek/deepseek-v4-flash"


def _apply_deep_seek_provider_config(cfg: OpenClawConfig) -> OpenClawConfig:
    defaults_models = cfg.get("agents", {}).get("defaults", {}).get("models")
    models = dict(defaults_models) if is_record(defaults_models) else {}
    existing = models.get(DEEPSEEK_DEFAULT_MODEL_REF)
    if is_record(existing):
        models[DEEPSEEK_DEFAULT_MODEL_REF] = {
            **existing,
            "alias": existing.get("alias") or "DeepSeek",
        }
    else:
        models[DEEPSEEK_DEFAULT_MODEL_REF] = {"alias": "DeepSeek"}

    return apply_provider_config_with_model_catalog(
        cfg,
        agent_models=models,
        provider_id="deepseek",
        api="openai-completions",
        base_url=DEEPSEEK_BASE_URL,
        catalog_models=[
            build_deep_seek_model_definition(model) for model in DEEPSEEK_MODEL_CATALOG
        ],
    )


def apply_deep_seek_config(cfg: OpenClawConfig) -> OpenClawConfig:
    return apply_agent_default_model_primary(
        _apply_deep_seek_provider_config(cfg),
        DEEPSEEK_DEFAULT_MODEL_REF,
    )
