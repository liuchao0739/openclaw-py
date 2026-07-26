"""Fireworks setup module handles plugin onboarding behavior."""

from __future__ import annotations

from openclaw.plugin_sdk.provider_onboard import (
    OpenClawConfig,
    create_default_models_preset_appliers,
)
from openclaw_extensions.fireworks.provider_catalog import (
    FIREWORKS_DEFAULT_MODEL_ID,
    build_fireworks_catalog_models,
    build_fireworks_provider,
)

FIREWORKS_DEFAULT_MODEL_REF = f"fireworks/{FIREWORKS_DEFAULT_MODEL_ID}"

_fireworks_preset_appliers = create_default_models_preset_appliers(
    primary_model_ref=FIREWORKS_DEFAULT_MODEL_REF,
    resolve_params=lambda _cfg: _resolve_fireworks_preset_params(),
)


def _resolve_fireworks_preset_params() -> dict[str, object]:
    default_provider = build_fireworks_provider()
    return {
        "provider_id": "fireworks",
        "api": default_provider.get("api") or "openai-completions",
        "base_url": default_provider["baseUrl"],
        "default_models": build_fireworks_catalog_models(),
        "default_model_id": FIREWORKS_DEFAULT_MODEL_ID,
        "aliases": [{"modelRef": FIREWORKS_DEFAULT_MODEL_REF, "alias": "Kimi K2.5 Turbo"}],
    }


def apply_fireworks_config(cfg: OpenClawConfig) -> OpenClawConfig:
    return _fireworks_preset_appliers["apply_config"](cfg)
