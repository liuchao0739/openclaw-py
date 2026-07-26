"""Cohere provider onboarding preset helpers."""

from __future__ import annotations

from openclaw.plugin_sdk.provider_onboard import (
    OpenClawConfig,
    create_model_catalog_preset_appliers,
)
from openclaw_extensions.cohere.models import (
    COHERE_BASE_URL,
    COHERE_MODEL_CATALOG,
    build_cohere_model_definition,
)

COHERE_DEFAULT_MODEL_ID = "command-a-03-2025"
COHERE_DEFAULT_MODEL_REF = f"cohere/{COHERE_DEFAULT_MODEL_ID}"

_cohere_preset_appliers = create_model_catalog_preset_appliers(
    primary_model_ref=COHERE_DEFAULT_MODEL_REF,
    resolve_params=lambda _cfg: {
        "provider_id": "cohere",
        "api": "openai-completions",
        "base_url": COHERE_BASE_URL,
        "catalog_models": [build_cohere_model_definition(model) for model in COHERE_MODEL_CATALOG],
        "aliases": [{"modelRef": COHERE_DEFAULT_MODEL_REF, "alias": "Cohere Command A"}],
    },
)


def apply_cohere_config(cfg: OpenClawConfig) -> OpenClawConfig:
    return _cohere_preset_appliers["apply_config"](cfg)
