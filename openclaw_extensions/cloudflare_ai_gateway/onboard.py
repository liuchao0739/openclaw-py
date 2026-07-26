"""Config patch helpers for Cloudflare AI Gateway onboarding flows."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from openclaw.packages.normalization_core import is_record
from openclaw.plugin_sdk.provider_onboard import (
    OpenClawConfig,
    apply_agent_default_model_primary,
    apply_provider_config_with_default_models,
)
from openclaw_extensions.cloudflare_ai_gateway.models import (
    CLOUDFLARE_AI_GATEWAY_DEFAULT_MODEL_ID,
    CLOUDFLARE_AI_GATEWAY_DEFAULT_MODEL_REF,
    build_cloudflare_ai_gateway_model_definition,
    resolve_cloudflare_ai_gateway_base_url,
)


def build_cloudflare_ai_gateway_config_patch(params: dict[str, str]) -> dict[str, Any]:
    base_url = resolve_cloudflare_ai_gateway_base_url(params)
    return {
        "models": {
            "providers": {
                "cloudflare-ai-gateway": {
                    "baseUrl": base_url,
                    "api": "anthropic-messages",
                    "models": [build_cloudflare_ai_gateway_model_definition()],
                },
            },
        },
        "agents": {
            "defaults": {
                "models": {
                    CLOUDFLARE_AI_GATEWAY_DEFAULT_MODEL_REF: {
                        "alias": "Cloudflare AI Gateway",
                    },
                },
            },
        },
    }


def apply_cloudflare_ai_gateway_provider_config(
    cfg: OpenClawConfig,
    params: dict[str, str | None] | None = None,
) -> OpenClawConfig:
    params = params or {}
    defaults_models = cfg.get("agents", {}).get("defaults", {}).get("models")
    models = dict(defaults_models) if is_record(defaults_models) else {}
    existing = models.get(CLOUDFLARE_AI_GATEWAY_DEFAULT_MODEL_REF)
    if is_record(existing):
        models[CLOUDFLARE_AI_GATEWAY_DEFAULT_MODEL_REF] = {
            **existing,
            "alias": existing.get("alias") or "Cloudflare AI Gateway",
        }
    else:
        models[CLOUDFLARE_AI_GATEWAY_DEFAULT_MODEL_REF] = {"alias": "Cloudflare AI Gateway"}

    providers = cfg.get("models", {}).get("providers")
    existing_provider = (
        providers.get("cloudflare-ai-gateway") if is_record(providers) else None
    )
    account_id = params.get("accountId")
    gateway_id = params.get("gatewayId")
    if account_id and gateway_id:
        base_url = resolve_cloudflare_ai_gateway_base_url(
            {"accountId": account_id, "gatewayId": gateway_id}
        )
    elif is_record(existing_provider) and isinstance(existing_provider.get("baseUrl"), str):
        base_url = existing_provider["baseUrl"]
    else:
        base_url = None

    if not base_url:
        next_cfg = deepcopy(cfg)
        agents = next_cfg.setdefault("agents", {})
        defaults = agents.setdefault("defaults", {})
        defaults["models"] = models
        return next_cfg

    return apply_provider_config_with_default_models(
        cfg,
        agent_models=models,
        provider_id="cloudflare-ai-gateway",
        api="anthropic-messages",
        base_url=base_url,
        default_models=[build_cloudflare_ai_gateway_model_definition()],
        default_model_id=CLOUDFLARE_AI_GATEWAY_DEFAULT_MODEL_ID,
    )


def apply_cloudflare_ai_gateway_config(
    cfg: OpenClawConfig,
    params: dict[str, str | None] | None = None,
) -> OpenClawConfig:
    return apply_agent_default_model_primary(
        apply_cloudflare_ai_gateway_provider_config(cfg, params),
        CLOUDFLARE_AI_GATEWAY_DEFAULT_MODEL_REF,
    )
