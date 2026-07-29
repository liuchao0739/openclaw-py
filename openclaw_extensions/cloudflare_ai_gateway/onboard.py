from copy import deepcopy
from typing import Any, Optional

from .models import (
    CLOUDFLARE_AI_GATEWAY_DEFAULT_MODEL_REF,
    build_cloudflare_ai_gateway_model_definition,
    resolve_cloudflare_ai_gateway_base_url,
)


def build_cloudflare_ai_gateway_config_patch(params: dict) -> dict:
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


def _apply_provider_config_with_default_model(
    cfg: dict, params: dict
) -> dict:
    cfg = deepcopy(cfg)
    providers = cfg.setdefault("models", {}).setdefault("providers", {})
    provider_id = params["providerId"]
    provider_entry = providers.setdefault(provider_id, {})
    provider_entry["api"] = params["api"]
    provider_entry["baseUrl"] = params["baseUrl"]
    provider_entry["models"] = params["defaultModel"]
    return cfg


def apply_cloudflare_ai_gateway_provider_config(
    cfg: Any, params: Optional[dict] = None
) -> Any:
    if not isinstance(cfg, dict):
        cfg = {}
    params = params or {}
    cfg = deepcopy(cfg)

    agents_cfg = cfg.get("agents", {})
    if not isinstance(agents_cfg, dict):
        agents_cfg = {}
    defaults_cfg = agents_cfg.get("defaults", {})
    if not isinstance(defaults_cfg, dict):
        defaults_cfg = {}
    models = dict(defaults_cfg.get("models", {}))
    existing = models.get(CLOUDFLARE_AI_GATEWAY_DEFAULT_MODEL_REF, {})
    merged = dict(existing) if isinstance(existing, dict) else {}
    merged.setdefault("alias", "Cloudflare AI Gateway")
    models[CLOUDFLARE_AI_GATEWAY_DEFAULT_MODEL_REF] = merged
    defaults_cfg["models"] = models
    agents_cfg["defaults"] = defaults_cfg
    cfg["agents"] = agents_cfg

    existing_provider = cfg.get("models", {}).get("providers", {}).get("cloudflare-ai-gateway", {})
    base_url: Optional[str] = None
    if params.get("accountId") and params.get("gatewayId"):
        base_url = resolve_cloudflare_ai_gateway_base_url({
            "accountId": params["accountId"],
            "gatewayId": params["gatewayId"],
        })
    elif isinstance(existing_provider.get("baseUrl"), str):
        base_url = existing_provider["baseUrl"]

    if not base_url:
        return cfg

    return _apply_provider_config_with_default_model(cfg, {
        "agentModels": models,
        "providerId": "cloudflare-ai-gateway",
        "api": "anthropic-messages",
        "baseUrl": base_url,
        "defaultModel": build_cloudflare_ai_gateway_model_definition(),
    })


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


def apply_cloudflare_ai_gateway_config(
    cfg: Any, params: Optional[dict] = None
) -> Any:
    cfg = apply_cloudflare_ai_gateway_provider_config(cfg, params)
    return _apply_agent_default_model_primary(cfg, CLOUDFLARE_AI_GATEWAY_DEFAULT_MODEL_REF)
