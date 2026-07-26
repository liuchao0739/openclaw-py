"""Tests for the Cloudflare AI Gateway provider extension."""

from __future__ import annotations

from typing import Any

from openclaw.plugin_sdk.plugin_test_runtime import create_captured_plugin_registration
from openclaw_extensions.cloudflare_ai_gateway.api import (
    CLOUDFLARE_AI_GATEWAY_DEFAULT_MODEL_ID,
    CLOUDFLARE_AI_GATEWAY_DEFAULT_MODEL_REF,
    CLOUDFLARE_AI_GATEWAY_PROVIDER_ID,
    apply_cloudflare_ai_gateway_config,
    apply_cloudflare_ai_gateway_provider_config,
    build_cloudflare_ai_gateway_catalog_provider,
    build_cloudflare_ai_gateway_config_patch,
    build_cloudflare_ai_gateway_model_definition,
    resolve_cloudflare_ai_gateway_base_url,
)
from openclaw_extensions.cloudflare_ai_gateway.index import default as cloudflare_plugin


def _register_provider() -> dict[str, Any]:
    captured = create_captured_plugin_registration(id="cloudflare-ai-gateway")
    cloudflare_plugin.register(captured.api)
    assert captured.providers, "expected Cloudflare AI Gateway provider"
    provider = captured.providers[0]
    assert provider["id"] == "cloudflare-ai-gateway"
    return provider


def test_exports_default_model_constants() -> None:
    assert CLOUDFLARE_AI_GATEWAY_PROVIDER_ID == "cloudflare-ai-gateway"
    assert CLOUDFLARE_AI_GATEWAY_DEFAULT_MODEL_ID == "claude-sonnet-4-6"
    assert CLOUDFLARE_AI_GATEWAY_DEFAULT_MODEL_REF == "cloudflare-ai-gateway/claude-sonnet-4-6"


def test_resolve_cloudflare_ai_gateway_base_url() -> None:
    assert (
        resolve_cloudflare_ai_gateway_base_url({"accountId": "acc-123", "gatewayId": "gw-456"})
        == "https://gateway.ai.cloudflare.com/v1/acc-123/gw-456/anthropic"
    )
    assert resolve_cloudflare_ai_gateway_base_url({"accountId": "", "gatewayId": "gw-456"}) == ""


def test_build_cloudflare_ai_gateway_model_definition_defaults() -> None:
    model = build_cloudflare_ai_gateway_model_definition()
    assert model["id"] == "claude-sonnet-4-6"
    assert model["name"] == "Claude Sonnet 4.6"
    assert model["reasoning"] is True
    assert model["input"] == ["text", "image"]
    assert model["contextWindow"] == 200_000
    assert model["maxTokens"] == 64_000


def test_build_cloudflare_ai_gateway_config_patch() -> None:
    patch = build_cloudflare_ai_gateway_config_patch(
        {"accountId": "acc-123", "gatewayId": "gw-456"}
    )
    provider = patch["models"]["providers"]["cloudflare-ai-gateway"]
    assert provider["baseUrl"] == "https://gateway.ai.cloudflare.com/v1/acc-123/gw-456/anthropic"
    assert provider["api"] == "anthropic-messages"
    assert provider["models"][0]["id"] == "claude-sonnet-4-6"
    assert (
        patch["agents"]["defaults"]["models"][CLOUDFLARE_AI_GATEWAY_DEFAULT_MODEL_REF]["alias"]
        == "Cloudflare AI Gateway"
    )


def test_apply_cloudflare_ai_gateway_provider_config_without_metadata_preserves_aliases() -> None:
    cfg = {
        "agents": {
            "defaults": {
                "models": {
                    CLOUDFLARE_AI_GATEWAY_DEFAULT_MODEL_REF: {"alias": "Custom Alias"},
                },
            },
        },
    }
    next_cfg = apply_cloudflare_ai_gateway_provider_config(cfg)
    assert (
        next_cfg["agents"]["defaults"]["models"][CLOUDFLARE_AI_GATEWAY_DEFAULT_MODEL_REF]["alias"]
        == "Custom Alias"
    )
    assert "models" not in next_cfg or "providers" not in next_cfg.get("models", {})


def test_apply_cloudflare_ai_gateway_config_sets_primary_model() -> None:
    cfg = apply_cloudflare_ai_gateway_config(
        {},
        {"accountId": "acc-123", "gatewayId": "gw-456"},
    )
    assert cfg["agents"]["defaults"]["model"]["primary"] == CLOUDFLARE_AI_GATEWAY_DEFAULT_MODEL_REF
    provider = cfg["models"]["providers"]["cloudflare-ai-gateway"]
    assert provider["baseUrl"] == "https://gateway.ai.cloudflare.com/v1/acc-123/gw-456/anthropic"


def test_build_cloudflare_ai_gateway_catalog_provider_requires_complete_metadata() -> None:
    assert (
        build_cloudflare_ai_gateway_catalog_provider(
            {
                "credential": {
                    "type": "api_key",
                    "key": "secret",
                },
            }
        )
        is None
    )


def test_build_cloudflare_ai_gateway_catalog_provider_env_managed_api_key() -> None:
    provider = build_cloudflare_ai_gateway_catalog_provider(
        {
            "credential": {
                "type": "api_key",
                "provider": "cloudflare-ai-gateway",
                "keyRef": {
                    "source": "env",
                    "provider": "default",
                    "id": "CLOUDFLARE_AI_GATEWAY_API_KEY",
                },
                "metadata": {
                    "accountId": "acc-123",
                    "gatewayId": "gw-456",
                },
            },
            "envApiKey": "CLOUDFLARE_AI_GATEWAY_API_KEY",
        }
    )
    assert provider is not None
    assert provider["baseUrl"] == "https://gateway.ai.cloudflare.com/v1/acc-123/gw-456/anthropic"
    assert provider["api"] == "anthropic-messages"
    assert provider["apiKey"] == "CLOUDFLARE_AI_GATEWAY_API_KEY"
    assert [model["id"] for model in provider["models"]] == ["claude-sonnet-4-6"]


def test_registers_stream_wrapper_that_strips_anthropic_thinking_assistant_prefill() -> None:
    provider = _register_provider()
    wrap_stream_fn = provider.get("wrapStreamFn")
    assert callable(wrap_stream_fn)

    captured_payload: dict[str, Any] | None = None

    def base_stream_fn(_model: Any, _context: Any, options: dict[str, Any] | None = None):
        nonlocal captured_payload
        payload: dict[str, Any] = {
            "thinking": {"type": "enabled", "budget_tokens": 1024},
            "messages": [
                {"role": "user", "content": "Return JSON."},
                {"role": "assistant", "content": "{"},
            ],
        }
        if options and options.get("onPayload"):
            options["onPayload"](payload, _model)
        captured_payload = payload
        return {}

    wrapped = wrap_stream_fn(
        {
            "provider": "cloudflare-ai-gateway",
            "modelId": "claude-sonnet-4-6",
            "model": {"api": "anthropic-messages"},
            "streamFn": base_stream_fn,
        }
    )
    assert callable(wrapped)
    wrapped(
        {"provider": "cloudflare-ai-gateway", "api": "anthropic-messages"},
        {},
        {},
    )

    assert captured_payload is not None
    assert captured_payload["messages"] == [{"role": "user", "content": "Return JSON."}]
