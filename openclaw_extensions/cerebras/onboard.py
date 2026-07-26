"""Cerebras onboarding config helpers."""

from __future__ import annotations

from openclaw.plugin_sdk.provider_onboard import (
    OpenClawConfig,
    create_model_catalog_preset_appliers,
)
from openclaw_extensions.cerebras.models import (
    CEREBRAS_BASE_URL,
    CEREBRAS_MODEL_CATALOG,
    build_cerebras_model_definition,
)

CEREBRAS_DEFAULT_MODEL_REF = "cerebras/zai-glm-4.7"

_cerebras_preset_appliers = create_model_catalog_preset_appliers(
    primary_model_ref=CEREBRAS_DEFAULT_MODEL_REF,
    resolve_params=lambda _cfg: {
        "provider_id": "cerebras",
        "api": "openai-completions",
        "base_url": CEREBRAS_BASE_URL,
        "catalog_models": [
            build_cerebras_model_definition(model) for model in CEREBRAS_MODEL_CATALOG
        ],
        "aliases": [{"modelRef": CEREBRAS_DEFAULT_MODEL_REF, "alias": "Cerebras GLM 4.7"}],
    },
)


def apply_cerebras_config(cfg: OpenClawConfig) -> OpenClawConfig:
    return _cerebras_preset_appliers["apply_config"](cfg)
