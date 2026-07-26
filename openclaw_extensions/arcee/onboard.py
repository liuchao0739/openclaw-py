"""Arcee setup preset appliers for direct API and OpenRouter-backed paths."""

from __future__ import annotations

from openclaw.plugin_sdk.provider_onboard import (
    OpenClawConfig,
    create_model_catalog_preset_appliers,
)
from openclaw_extensions.arcee.models import ARCEE_BASE_URL
from openclaw_extensions.arcee.provider_catalog import (
    OPENROUTER_BASE_URL,
    build_arcee_catalog_models,
    build_arcee_open_router_catalog_models,
)

ARCEE_DEFAULT_MODEL_REF = "arcee/trinity-large-thinking"
ARCEE_OPENROUTER_DEFAULT_MODEL_REF = "arcee/trinity-large-thinking"

_arcee_preset_appliers = create_model_catalog_preset_appliers(
    primary_model_ref=ARCEE_DEFAULT_MODEL_REF,
    resolve_params=lambda _cfg: {
        "provider_id": "arcee",
        "api": "openai-completions",
        "base_url": ARCEE_BASE_URL,
        "catalog_models": build_arcee_catalog_models(),
        "aliases": [{"modelRef": ARCEE_DEFAULT_MODEL_REF, "alias": "Arcee AI"}],
    },
)

_arcee_open_router_preset_appliers = create_model_catalog_preset_appliers(
    primary_model_ref=ARCEE_OPENROUTER_DEFAULT_MODEL_REF,
    resolve_params=lambda _cfg: {
        "provider_id": "arcee",
        "api": "openai-completions",
        "base_url": OPENROUTER_BASE_URL,
        "catalog_models": build_arcee_open_router_catalog_models(),
        "aliases": [
            {
                "modelRef": ARCEE_OPENROUTER_DEFAULT_MODEL_REF,
                "alias": "Arcee AI (OpenRouter)",
            }
        ],
    },
)


def apply_arcee_config(cfg: OpenClawConfig) -> OpenClawConfig:
    return _arcee_preset_appliers["apply_config"](cfg)


def apply_arcee_open_router_config(cfg: OpenClawConfig) -> OpenClawConfig:
    return _arcee_open_router_preset_appliers["apply_config"](cfg)
