"""Tests for Copilot BYOK provider mapping behavior."""

from __future__ import annotations

import pytest

from openclaw_extensions.copilot.src.provider_bridge import (
    COPILOT_BYOK_ENDPOINT_POLICY_ERROR,
    COPILOT_BYOK_PROVIDER_ERROR,
    COPILOT_BYOK_TRANSPORT_POLICY_ERROR,
    resolve_copilot_provider,
    supports_copilot_byok_provider_shape,
)


def test_keeps_the_subscription_provider_on_the_native_copilot_auth_path() -> None:
    assert resolve_copilot_provider(
        model={
            "provider": "github-copilot",
            "api": "github-copilot",
            "id": "gpt-5",
            "base_url": "https://ignored.example",
        },
        resolved_api_key="ignored",
    ) == {"mode": "github-copilot"}


def test_maps_openai_responses_byok_with_a_bearer_token_and_stable_limits() -> None:
    result = resolve_copilot_provider(
        model={
            "provider": "local-proxy",
            "api": "openai-responses",
            "id": "proxy-model",
            "base_url": "https://proxy.example/v1",
            "auth_header": True,
            "context_tokens": 12_000,
            "max_tokens": 512,
            "headers": {"X-Trace": "test"},
        },
        resolved_api_key="secret-key",
        auth_profile_id="local-proxy:main",
    )

    assert result["mode"] == "byok"
    assert result["auth_profile_id"] == "local-proxy:main"
    assert result["auth_profile_version"].startswith("sha256:")
    assert result["provider"] == {
        "type": "openai",
        "wire_api": "responses",
        "base_url": "https://proxy.example/v1",
        "model_id": "proxy-model",
        "wire_model": "proxy-model",
        "bearer_token": "secret-key",
        "headers": {"X-Trace": "test"},
        "max_prompt_tokens": 12_000,
        "max_output_tokens": 512,
    }


def test_defaults_custom_byok_providers_without_an_api_to_openai_responses() -> None:
    result = resolve_copilot_provider(
        model={
            "provider": "custom-proxy",
            "id": "proxy-model",
            "base_url": "https://proxy.example/v1",
        },
        resolved_api_key="secret-key",
    )

    assert result["provider"] == {
        "type": "openai",
        "wire_api": "responses",
        "base_url": "https://proxy.example/v1",
        "model_id": "proxy-model",
        "wire_model": "proxy-model",
        "api_key": "secret-key",
    }
    assert supports_copilot_byok_provider_shape({"base_url": "https://proxy.example/v1"}) is True


def test_changes_the_byok_compatibility_fingerprint_when_token_limits_change() -> None:
    base = {
        "provider": "custom-proxy",
        "api": "openai-responses",
        "id": "proxy-model",
        "base_url": "https://proxy.example/v1",
    }

    small = resolve_copilot_provider(
        model={**base, "context_tokens": 8_000, "max_tokens": 512},
        resolved_api_key="secret-key",
    )
    large = resolve_copilot_provider(
        model={**base, "context_tokens": 16_000, "max_tokens": 1024},
        resolved_api_key="secret-key",
    )

    assert small["auth_profile_version"] != large["auth_profile_version"]


def test_maps_anthropic_and_ollama_compatible_apis() -> None:
    assert resolve_copilot_provider(
        model={
            "provider": "anthropic-proxy",
            "api": "anthropic-messages",
            "id": "claude",
            "base_url": "https://anthropic.example",
        },
    )["provider"] == {
        "type": "anthropic",
        "base_url": "https://anthropic.example",
        "model_id": "claude",
        "wire_model": "claude",
    }

    assert resolve_copilot_provider(
        model={
            "provider": "ollama-compatible",
            "api": "ollama",
            "id": "qwen",
            "base_url": "https://ollama-compatible.example/v1",
        },
    )["provider"] == {
        "type": "openai",
        "wire_api": "completions",
        "base_url": "https://ollama-compatible.example/v1",
        "model_id": "qwen",
        "wire_model": "qwen",
    }


def test_normalizes_azure_openai_responses_config_for_the_copilot_sdk_provider_contract() -> None:
    result = resolve_copilot_provider(
        model={
            "provider": "custom-azure",
            "api": "azure-openai-responses",
            "id": "deployment-gpt",
            "base_url": "https://example.openai.azure.com/openai/v1",
            "azure_api_version": "2025-01-01-preview",
        },
        resolved_api_key="azure-key",
    )

    assert result["provider"] == {
        "type": "azure",
        "wire_api": "responses",
        "base_url": "https://example.openai.azure.com",
        "model_id": "deployment-gpt",
        "wire_model": "deployment-gpt",
        "api_key": "azure-key",
        "azure": {"apiVersion": "2025-01-01-preview"},
    }
    assert resolve_copilot_provider(
        model={
            "provider": "custom-azure",
            "api": "azure-openai-responses",
            "id": "deployment-gpt",
            "base_url": "https://example.cognitiveservices.azure.com/openai/v1",
        },
    )["provider"] == {
        "type": "azure",
        "wire_api": "responses",
        "base_url": "https://example.cognitiveservices.azure.com",
        "model_id": "deployment-gpt",
        "wire_model": "deployment-gpt",
    }
    assert resolve_copilot_provider(
        model={
            "provider": "custom-azure",
            "api": "azure-openai-responses",
            "id": "deployment",
            "base_url": "https://example.cognitiveservices.azure.com/openai/v1",
        },
    )["provider"] == {
        "type": "azure",
        "wire_api": "responses",
        "base_url": "https://example.cognitiveservices.azure.com",
        "model_id": "deployment",
        "wire_model": "deployment",
    }
    assert resolve_copilot_provider(
        model={
            "provider": "custom-azure",
            "api": "azure-openai-responses",
            "id": "deployment-gpt",
            "base_url": "https://project.services.ai.azure.com/api/projects/demo/openai/v1",
        },
        resolved_api_key="azure-key",
    )["provider"] == {
        "type": "openai",
        "wire_api": "responses",
        "base_url": "https://project.services.ai.azure.com/api/projects/demo/openai/v1",
        "model_id": "deployment-gpt",
        "wire_model": "deployment-gpt",
        "api_key": "azure-key",
    }


def test_does_not_forward_local_auth_markers_or_null_no_auth_headers() -> None:
    result = resolve_copilot_provider(
        model={
            "provider": "local-proxy",
            "api": "openai-completions",
            "id": "local-model",
            "base_url": "https://proxy.example/v1",
            "auth_header": True,
            "headers": {
                "Authorization": None,
                "X-Local": "true",
            },
        },
        resolved_api_key="custom-local",
    )

    assert result["provider"] == {
        "type": "openai",
        "wire_api": "completions",
        "base_url": "https://proxy.example/v1",
        "model_id": "local-model",
        "wire_model": "local-model",
        "headers": {"X-Local": "true"},
    }


def test_does_not_synthesize_sdk_api_key_auth_when_request_auth_already_prepared_headers() -> None:
    result = resolve_copilot_provider(
        model={
            "provider": "custom-header-proxy",
            "api": "openai-responses",
            "id": "proxy-model",
            "base_url": "https://proxy.example/v1",
            "headers": {"x-api-key": "header-secret"},
            "request_auth_mode": "header",
        },
        resolved_api_key="header-secret",
    )

    assert result["provider"] == {
        "type": "openai",
        "wire_api": "responses",
        "base_url": "https://proxy.example/v1",
        "model_id": "proxy-model",
        "wire_model": "proxy-model",
        "headers": {"x-api-key": "header-secret"},
    }


@pytest.mark.parametrize(
    "model",
    [
        {"request_proxy": {"mode": "env-proxy"}},
        {"request_tls": {"ca": "ca-pem"}},
        {"request_allow_private_network": False},
    ],
)
def test_rejects_request_transport_policy_the_sdk_provider_config_cannot_enforce(
    model: dict[str, object],
) -> None:
    with pytest.raises(ValueError) as exc_info:
        resolve_copilot_provider(
            model={
                "provider": "custom-proxy",
                "api": "openai-responses",
                "id": "proxy-model",
                "base_url": "https://proxy.example/v1",
                **model,
            },
        )
    assert str(exc_info.value) == COPILOT_BYOK_TRANSPORT_POLICY_ERROR


@pytest.mark.parametrize(
    "base_url",
    [
        "file://public.example/v1",
        "ftp://public.example/v1",
        "http://proxy.example/v1",
        "https://user:pass@proxy.example/v1",
        "https://proxy.example/v1?api_key=secret",
        "https://proxy.example/v1?x-api-key=secret",
        "https://proxy.example/v1?x-auth-token=secret",
        "https://proxy.example/v1?password=secret",
        "https://proxy.example/v1?client%5Fse%E2%80%8Bcret=secret",
        "http://169.254.169.254/v1",
        "http://metadata.google.internal/v1",
        "http://localhost:11434/v1",
    ],
)
def test_rejects_byok_endpoints_blocked_by_openclaw_ssrf_policy(base_url: str) -> None:
    with pytest.raises(ValueError) as exc_info:
        resolve_copilot_provider(
            model={
                "provider": "custom-proxy",
                "api": "openai-responses",
                "id": "proxy-model",
                "base_url": base_url,
            },
        )
    assert str(exc_info.value) == COPILOT_BYOK_ENDPOINT_POLICY_ERROR


def test_advertises_support_only_for_representable_byok_provider_shapes() -> None:
    assert (
        supports_copilot_byok_provider_shape(
            {
                "api": "openai-responses",
                "base_url": "https://proxy.example/v1",
            }
        )
        is True
    )
    assert (
        supports_copilot_byok_provider_shape(
            {
                "api": "azure-openai-responses",
                "base_url": "https://example.openai.azure.com/openai/v1",
            }
        )
        is True
    )
    assert (
        supports_copilot_byok_provider_shape(
            {
                "api": "azure-openai-responses",
                "base_url": "https://project.services.ai.azure.com/api/projects/demo/openai/v1",
            }
        )
        is True
    )
    assert (
        supports_copilot_byok_provider_shape(
            {
                "api": "azure-openai-responses",
                "base_url": "https://project.services.ai.azure.com/api/projects/demo",
            }
        )
        is False
    )
    assert (
        supports_copilot_byok_provider_shape(
            {
                "api": "google-generative-ai",
                "base_url": "https://google.example",
            }
        )
        is False
    )
    assert (
        supports_copilot_byok_provider_shape(
            {
                "api": "openai-responses",
                "base_url": "file://public.example/v1",
            }
        )
        is False
    )
    assert (
        supports_copilot_byok_provider_shape(
            {
                "api": "openai-responses",
                "base_url": "http://proxy.example/v1",
            }
        )
        is False
    )
    assert (
        supports_copilot_byok_provider_shape(
            {
                "api": "openai-responses",
                "base_url": "https://user:pass@proxy.example/v1",
            }
        )
        is False
    )
    assert (
        supports_copilot_byok_provider_shape(
            {
                "api": "openai-responses",
                "base_url": "https://proxy.example/v1?api_key=secret",
            }
        )
        is False
    )
    assert (
        supports_copilot_byok_provider_shape(
            {
                "api": "openai-responses",
                "base_url": "https://proxy.example/v1?x-api-key=secret",
            }
        )
        is False
    )
    assert supports_copilot_byok_provider_shape({"api": "openai-responses"}) is False
    assert (
        supports_copilot_byok_provider_shape(
            {
                "api": "openai-responses",
                "base_url": "https://proxy.example/v1",
                "request_proxy": {"mode": "env-proxy"},
            }
        )
        is False
    )


def test_rejects_provider_apis_the_sdk_adapter_cannot_represent() -> None:
    with pytest.raises(ValueError) as exc_info:
        resolve_copilot_provider(
            model={
                "provider": "google",
                "api": "google-generative-ai",
                "id": "gemini",
                "base_url": "https://google.example",
            },
        )
    assert str(exc_info.value) == COPILOT_BYOK_PROVIDER_ERROR


def test_requires_an_endpoint_for_non_subscription_providers() -> None:
    with pytest.raises(ValueError) as exc_info:
        resolve_copilot_provider(
            model={
                "provider": "custom",
                "api": "openai-completions",
                "id": "model",
            },
        )
    assert str(exc_info.value) == COPILOT_BYOK_PROVIDER_ERROR
