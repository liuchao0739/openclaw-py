"""Tests for provider model id policy normalization."""

from __future__ import annotations

from openclaw_packages.model_catalog_core import (
    collect_manifest_model_id_normalization_policies,
    normalize_configured_provider_catalog_model_id,
    normalize_static_provider_model_id_with_policies,
    strip_self_provider_model_prefix,
)


def test_applies_manifest_policies_before_built_in_provider_normalization() -> None:
    policies = collect_manifest_model_id_normalization_policies(
        [
            {
                "modelIdNormalization": {
                    "providers": {
                        "Google-Vertex": {
                            "aliases": {
                                "pro": "gemini-3-pro",
                            },
                        },
                    },
                },
            },
        ],
    )

    assert normalize_static_provider_model_id_with_policies("google-vertex", "pro", policies) == (
        "gemini-3.1-pro-preview"
    )


def test_normalizes_provider_prefixed_google_catalog_refs_behind_gateway_prefixes() -> None:
    assert normalize_configured_provider_catalog_model_id(
        "openrouter",
        "openrouter/google/gemini-3-pro-preview",
    ) == "openrouter/google/gemini-3.1-pro-preview"
    assert normalize_configured_provider_catalog_model_id(
        "openrouter",
        "openrouter/google/gemma-4-26b",
    ) == "openrouter/google/gemma-4-26b-a4b-it"


def test_normalizes_native_anthropic_catalog_refs_without_retaining_provider_prefix() -> None:
    assert normalize_static_provider_model_id_with_policies(
        "anthropic",
        "anthropic/claude-haiku-4-5",
    ) == "claude-haiku-4-5"
    assert normalize_configured_provider_catalog_model_id(
        "anthropic",
        "anthropic/claude-haiku-4-5",
    ) == "claude-haiku-4-5"


def test_normalizes_provider_prefixed_native_catalog_refs_without_stripping_catalog_prefixes() -> (
    None
):
    assert normalize_static_provider_model_id_with_policies(
        "google",
        "google/gemini-2.0-flash",
    ) == "google/gemini-2.0-flash"
    assert normalize_static_provider_model_id_with_policies(
        "google-gemini-cli",
        "google-gemini-cli/gemini-2.0-flash",
    ) == "google-gemini-cli/gemini-2.0-flash"
    assert normalize_static_provider_model_id_with_policies(
        "google-vertex",
        "google-vertex/gemini-3-pro-preview",
    ) == "google-vertex/gemini-3-pro-preview"
    assert normalize_static_provider_model_id_with_policies(
        "xai",
        "xai/grok-4-fast-reasoning",
    ) == "xai/grok-4-fast-reasoning"
    assert normalize_static_provider_model_id_with_policies(
        "openai",
        "openai/gpt-5.4",
    ) == "openai/gpt-5.4"
    assert normalize_static_provider_model_id_with_policies(
        "vercel-ai-gateway",
        "vercel-ai-gateway/opus-4.6",
    ) == "vercel-ai-gateway/opus-4.6"


def test_strips_self_provider_model_prefixes_before_runtime_provider_calls() -> None:
    assert strip_self_provider_model_prefix("google", "google/gemini-2.0-flash") == (
        "gemini-2.0-flash"
    )
    assert strip_self_provider_model_prefix("xai", "xai/grok-4-fast-reasoning") == (
        "grok-4-fast-reasoning"
    )
    assert strip_self_provider_model_prefix("openai", "openai/gpt-5.4") == "gpt-5.4"
    assert strip_self_provider_model_prefix("vercel-ai-gateway", "vercel-ai-gateway/opus-4.6") == (
        "opus-4.6"
    )


def _strip_with(strip_prefixes: list[str], model_id: str) -> str:
    policies = collect_manifest_model_id_normalization_policies(
        [
            {
                "modelIdNormalization": {
                    "providers": {
                        "openai": {"stripPrefixes": strip_prefixes},
                    },
                },
            },
        ],
    )
    return normalize_static_provider_model_id_with_policies("openai", model_id, policies)


def test_strips_whitespace_free_prefix_exactly() -> None:
    assert _strip_with(["openai/"], "openai/gpt-4") == "gpt-4"


def test_strips_by_matched_length_when_manifest_prefix_has_leading_space() -> None:
    assert _strip_with([" openai/"], "openai/gpt-4") == "gpt-4"


def test_strips_by_matched_length_when_manifest_prefix_has_trailing_space() -> None:
    assert _strip_with(["openai/ "], "openai/gpt-4") == "gpt-4"


def test_strips_by_matched_length_when_manifest_prefix_differs_in_case_and_spacing() -> None:
    assert _strip_with([" OpenAI/ "], "openai/gpt-4") == "gpt-4"
