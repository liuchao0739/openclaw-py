"""Cloudflare AI Gateway provider extension."""

from openclaw_extensions.cloudflare_ai_gateway.api import (
    CLOUDFLARE_AI_GATEWAY_DEFAULT_MODEL_ID,
    CLOUDFLARE_AI_GATEWAY_DEFAULT_MODEL_REF,
    CLOUDFLARE_AI_GATEWAY_PROVIDER_ID,
    apply_cloudflare_ai_gateway_config,
    apply_cloudflare_ai_gateway_provider_config,
    build_cloudflare_ai_gateway_catalog_provider,
    build_cloudflare_ai_gateway_config_patch,
    build_cloudflare_ai_gateway_model_definition,
    create_cloudflare_ai_gateway_anthropic_thinking_prefill_wrapper,
    resolve_cloudflare_ai_gateway_base_url,
    testing,
    wrap_cloudflare_ai_gateway_provider_stream,
)

__all__ = [
    "CLOUDFLARE_AI_GATEWAY_DEFAULT_MODEL_ID",
    "CLOUDFLARE_AI_GATEWAY_DEFAULT_MODEL_REF",
    "CLOUDFLARE_AI_GATEWAY_PROVIDER_ID",
    "apply_cloudflare_ai_gateway_config",
    "apply_cloudflare_ai_gateway_provider_config",
    "build_cloudflare_ai_gateway_catalog_provider",
    "build_cloudflare_ai_gateway_config_patch",
    "build_cloudflare_ai_gateway_model_definition",
    "create_cloudflare_ai_gateway_anthropic_thinking_prefill_wrapper",
    "resolve_cloudflare_ai_gateway_base_url",
    "testing",
    "wrap_cloudflare_ai_gateway_provider_stream",
]
