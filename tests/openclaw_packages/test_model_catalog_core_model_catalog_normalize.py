"""Tests for model catalog normalization."""

from __future__ import annotations

from openclaw_packages.model_catalog_core import (
    build_model_catalog_merge_key,
    build_model_catalog_ref,
    normalize_model_catalog,
    normalize_model_catalog_rows,
)


def test_normalizes_catalog_ownership_aliases_suppressions_and_row_fields() -> None:
    catalog = normalize_model_catalog(
        {
            "providers": {
                "OpenAI": {
                    "baseUrl": "https://api.openai.com/v1",
                    "api": "openai-responses",
                    "headers": {
                        "x-provider": "openai",
                    },
                    "models": [
                        {
                            "id": "gpt-5.4",
                            "name": "GPT-5.4",
                            "api": "openai-completions",
                            "baseUrl": "https://proxy.example/v1",
                            "headers": {
                                "x-model": "gpt-5.4",
                            },
                            "input": ["text", "image", "document", "audio"],
                            "reasoning": True,
                            "contextWindow": 256000,
                            "contextTokens": 200000,
                            "maxTokens": 128000,
                            "cost": {
                                "input": 1.25,
                                "output": 10,
                                "cacheRead": 0.125,
                                "tieredPricing": [
                                    {
                                        "input": 1.25,
                                        "output": 10,
                                        "cacheRead": 0.125,
                                        "cacheWrite": 1.25,
                                        "range": [0, 256000],
                                    },
                                    {
                                        "input": 1,
                                        "output": 2,
                                        "range": [0, 1000],
                                    },
                                ],
                            },
                            "compat": {
                                "supportsTools": True,
                                "openRouterRouting": {
                                    "only": ["anthropic", 1],
                                    "allow_fallbacks": False,
                                    "require_parameters": "no",
                                },
                                "vercelGatewayRouting": {
                                    "order": ["anthropic", 1],
                                    "only": "openai",
                                },
                                "zaiToolStream": True,
                                "cacheControlFormat": "anthropic",
                                "sendSessionAffinityHeaders": True,
                                "sendSessionIdHeader": False,
                                "supportsEagerToolInputStreaming": False,
                                "supportsLongCacheRetention": True,
                                "supportsStore": "yes",
                                "thinkingFormat": "together",
                                "unknownFlag": True,
                            },
                            "status": "preview",
                            "statusReason": "rolling out",
                            "replaces": ["gpt-5.3"],
                            "replacedBy": "gpt-5.5",
                            "tags": ["default"],
                        },
                        {
                            "id": "",
                        },
                    ],
                },
                "anthropic": {
                    "models": [{"id": "claude-sonnet-4.6"}],
                },
            },
            "aliases": {
                "Azure-OpenAI-Responses": {
                    "provider": "OpenAI",
                    "api": "azure-openai-responses",
                },
                "anthropic-alias": {
                    "provider": "anthropic",
                },
            },
            "suppressions": [
                {
                    "provider": "Azure-OpenAI-Responses",
                    "model": "gpt-5.3-codex-spark",
                    "reason": "not available",
                    "when": {
                        "baseUrlHosts": ["CODING-INTL.DASHSCOPE.ALIYUNCS.COM"],
                        "providerConfigApiIn": ["Qwen", "ModelStudio"],
                    },
                },
            ],
            "discovery": {
                "OpenAI": "static",
                "anthropic": "static",
                "bad": "unknown",
            },
            "runtimeAugment": True,
        },
        owned_providers={"OpenAI"},
    )

    assert catalog == {
        "providers": {
            "openai": {
                "baseUrl": "https://api.openai.com/v1",
                "api": "openai-responses",
                "headers": {
                    "x-provider": "openai",
                },
                "models": [
                    {
                        "id": "gpt-5.4",
                        "name": "GPT-5.4",
                        "api": "openai-completions",
                        "baseUrl": "https://proxy.example/v1",
                        "headers": {
                            "x-model": "gpt-5.4",
                        },
                        "input": ["text", "image", "document"],
                        "reasoning": True,
                        "contextWindow": 256000,
                        "contextTokens": 200000,
                        "maxTokens": 128000,
                        "cost": {
                            "input": 1.25,
                            "output": 10,
                            "cacheRead": 0.125,
                            "tieredPricing": [
                                {
                                    "input": 1.25,
                                    "output": 10,
                                    "cacheRead": 0.125,
                                    "cacheWrite": 1.25,
                                    "range": (0, 256000),
                                },
                            ],
                        },
                        "compat": {
                            "supportsTools": True,
                            "openRouterRouting": {
                                "only": ["anthropic"],
                                "allow_fallbacks": False,
                            },
                            "vercelGatewayRouting": {"order": ["anthropic"]},
                            "zaiToolStream": True,
                            "cacheControlFormat": "anthropic",
                            "sendSessionAffinityHeaders": True,
                            "sendSessionIdHeader": False,
                            "supportsEagerToolInputStreaming": False,
                            "supportsLongCacheRetention": True,
                            "thinkingFormat": "together",
                        },
                        "status": "preview",
                        "statusReason": "rolling out",
                        "replaces": ["gpt-5.3"],
                        "replacedBy": "gpt-5.5",
                        "tags": ["default"],
                    },
                ],
            },
        },
        "aliases": {
            "azure-openai-responses": {
                "provider": "openai",
                "api": "azure-openai-responses",
            },
        },
        "suppressions": [
            {
                "provider": "azure-openai-responses",
                "model": "gpt-5.3-codex-spark",
                "reason": "not available",
                "when": {
                    "baseUrlHosts": ["coding-intl.dashscope.aliyuncs.com"],
                    "providerConfigApiIn": ["qwen", "modelstudio"],
                },
            },
        ],
        "discovery": {
            "openai": "static",
        },
        "runtimeAugment": True,
    }


def test_builds_normalized_rows_with_provider_defaults_and_stable_refs() -> None:
    rows = normalize_model_catalog_rows(
        source="manifest",
        providers={
            "OpenAI": {
                "baseUrl": "https://api.openai.com/v1",
                "api": "openai-responses",
                "headers": {
                    "x-provider": "openai",
                },
                "models": [
                    {
                        "id": "GPT-5.4",
                        "headers": {
                            "x-model": "gpt-5.4",
                        },
                        "input": ["image"],
                    },
                ],
            },
        },
    )

    assert rows == [
        {
            "provider": "openai",
            "id": "GPT-5.4",
            "ref": "openai/GPT-5.4",
            "mergeKey": "openai::gpt-5.4",
            "name": "GPT-5.4",
            "source": "manifest",
            "input": ["image"],
            "reasoning": False,
            "status": "available",
            "api": "openai-responses",
            "baseUrl": "https://api.openai.com/v1",
            "headers": {
                "x-provider": "openai",
                "x-model": "gpt-5.4",
            },
        },
    ]
    assert build_model_catalog_ref("OpenAI", "GPT-5.4") == "openai/GPT-5.4"
    assert build_model_catalog_merge_key("OpenAI", "GPT-5.4") == "openai::gpt-5.4"
