"""Chutes onboarding config helpers for OAuth and API-key setup."""

from __future__ import annotations

from openclaw.plugin_sdk.provider_onboard import (
    OpenClawConfig,
    apply_agent_default_model_primary,
    apply_provider_config_with_model_catalog_preset,
)
from openclaw_extensions.chutes.models import (
    CHUTES_BASE_URL,
    CHUTES_DEFAULT_MODEL_REF,
    CHUTES_MODEL_CATALOG,
    build_chutes_model_definition,
)

__all__ = [
    "CHUTES_DEFAULT_MODEL_REF",
    "apply_chutes_api_key_config",
    "apply_chutes_config",
    "apply_chutes_provider_config",
]


def apply_chutes_provider_config(cfg: OpenClawConfig) -> OpenClawConfig:
    """Apply Chutes provider configuration without changing the default model."""
    return apply_provider_config_with_model_catalog_preset(
        cfg,
        provider_id="chutes",
        api="openai-completions",
        base_url=CHUTES_BASE_URL,
        catalog_models=[
            build_chutes_model_definition(model) for model in CHUTES_MODEL_CATALOG
        ],
        aliases=[
            *[f"chutes/{model['id']}" for model in CHUTES_MODEL_CATALOG],
            {"modelRef": "chutes-fast", "alias": "chutes/zai-org/GLM-4.7-FP8"},
            {
                "modelRef": "chutes-vision",
                "alias": "chutes/chutesai/Mistral-Small-3.2-24B-Instruct-2506",
            },
            {"modelRef": "chutes-pro", "alias": "chutes/deepseek-ai/DeepSeek-V3.2-TEE"},
        ],
    )


def apply_chutes_config(cfg: OpenClawConfig) -> OpenClawConfig:
    """Apply Chutes provider configuration and set Chutes as the default model."""
    next_cfg = apply_chutes_provider_config(cfg)
    agents = dict(next_cfg.get("agents") or {})
    defaults = dict(agents.get("defaults") or {})
    defaults["model"] = {
        "primary": CHUTES_DEFAULT_MODEL_REF,
        "fallbacks": [
            "chutes/deepseek-ai/DeepSeek-V3.2-TEE",
            "chutes/Qwen/Qwen3-32B",
        ],
    }
    defaults["imageModel"] = {
        "primary": "chutes/chutesai/Mistral-Small-3.2-24B-Instruct-2506",
        "fallbacks": ["chutes/chutesai/Mistral-Small-3.1-24B-Instruct-2503"],
    }
    agents["defaults"] = defaults
    next_cfg["agents"] = agents
    return next_cfg


def apply_chutes_api_key_config(cfg: OpenClawConfig) -> OpenClawConfig:
    """Apply Chutes provider config and set the default model for API-key auth."""
    return apply_agent_default_model_primary(
        apply_chutes_provider_config(cfg),
        CHUTES_DEFAULT_MODEL_REF,
    )
