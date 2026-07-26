"""Tests for the Arcee AI provider extension."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from openclaw.plugin_sdk.plugin_test_runtime import create_captured_plugin_registration
from openclaw_extensions.arcee.api import (
    ARCEE_BASE_URL,
    ARCEE_DEFAULT_MODEL_REF,
    ARCEE_MODEL_CATALOG,
    ARCEE_OPENROUTER_DEFAULT_MODEL_REF,
    OPENROUTER_BASE_URL,
    apply_arcee_config,
    apply_arcee_open_router_config,
    build_arcee_catalog_models,
    build_arcee_model_definition,
    build_arcee_open_router_catalog_models,
    build_arcee_open_router_provider,
    build_arcee_provider,
    normalize_arcee_open_router_base_url,
    to_arcee_open_router_model_id,
)
from openclaw_extensions.arcee.index import (
    default as arcee_plugin,
)
from openclaw_extensions.arcee.index import (
    normalize_arcee_resolved_model,
    resolve_arcee_catalog,
)

_MANIFEST_PATH = (
    Path(__file__).resolve().parents[2] / "openclaw_extensions" / "arcee" / "openclaw.plugin.json"
)


def _read_manifest() -> dict[str, Any]:
    return json.loads(_MANIFEST_PATH.read_text(encoding="utf-8"))


def _resolve_provider_choice(provider: dict[str, Any], choice_id: str) -> dict[str, Any] | None:
    for method in provider.get("auth", []):
        wizard = method.get("wizard", {})
        if wizard.get("choiceId") == choice_id:
            return {"provider": provider, "method": method}
    return None


async def _run_single_provider_catalog(
    provider: dict[str, Any],
    *,
    resolve_provider_api_key: Any,
) -> dict[str, Any]:
    catalog = provider.get("catalog", {})
    run = catalog.get("run")
    if run is None:
        build_provider = catalog.get("buildProvider") or catalog.get("buildStaticProvider")
        if build_provider is None:
            raise ValueError("expected provider catalog runner")
        return build_provider()
    result = await run({"resolveProviderApiKey": resolve_provider_api_key})
    if not result or "provider" not in result:
        raise ValueError("expected provider catalog result")
    return result["provider"]


def test_registers_arcee_ai_with_direct_and_openrouter_auth_choices() -> None:
    captured = create_captured_plugin_registration(id="arcee")
    arcee_plugin.register(captured.api)
    assert captured.providers, "expected Arcee provider registration"
    provider = captured.providers[0]

    assert provider["id"] == "arcee"
    assert provider["label"] == "Arcee AI"
    assert provider["envVars"] == ["ARCEEAI_API_KEY", "OPENROUTER_API_KEY"]
    assert len(provider["auth"]) == 2

    direct_choice = _resolve_provider_choice(provider, "arceeai-api-key")
    assert direct_choice is not None
    assert direct_choice["provider"]["id"] == "arcee"
    assert direct_choice["method"]["id"] == "arcee-platform"

    open_router_choice = _resolve_provider_choice(provider, "arceeai-openrouter")
    assert open_router_choice is not None
    assert open_router_choice["provider"]["id"] == "arcee"
    assert open_router_choice["method"]["id"] == "openrouter"


def test_stores_the_openrouter_onboarding_path_under_the_openrouter_auth_profile() -> None:
    config = apply_arcee_open_router_config({})
    arcee_config = config.get("models", {}).get("providers", {}).get("arcee")

    assert arcee_config is not None
    assert arcee_config["baseUrl"] == OPENROUTER_BASE_URL
    assert arcee_config["api"] == "openai-completions"
    assert [model["id"] for model in arcee_config["models"]] == [
        "arcee/trinity-mini",
        "arcee/trinity-large-preview",
        "arcee/trinity-large-thinking",
    ]


def test_keeps_direct_arcee_auth_env_candidates_separate_from_openrouter() -> None:
    manifest = _read_manifest()
    assert manifest["setup"]["providers"] == [{"id": "arcee", "envVars": ["ARCEEAI_API_KEY"]}]
    assert manifest["providerAuthChoices"][0]["cliFlag"] == "--arceeai-api-key"
    assert manifest["providerAuthChoices"][1]["cliFlag"] == "--openrouter-api-key"


@pytest.mark.asyncio
async def test_builds_the_direct_arcee_ai_model_catalog() -> None:
    captured = create_captured_plugin_registration(id="arcee")
    arcee_plugin.register(captured.api)
    provider = captured.providers[0]

    catalog_provider = await _run_single_provider_catalog(
        provider,
        resolve_provider_api_key=lambda provider_id=None: (
            {"apiKey": "test-key"} if provider_id == "arcee" else {"apiKey": None}
        ),
    )

    assert catalog_provider["api"] == "openai-completions"
    assert catalog_provider["baseUrl"] == ARCEE_BASE_URL
    assert [model["id"] for model in catalog_provider["models"]] == [
        "trinity-mini",
        "trinity-large-preview",
        "trinity-large-thinking",
    ]
    thinking_compat = next(
        model["compat"]
        for model in catalog_provider["models"]
        if model["id"] == "trinity-large-thinking"
    )
    assert thinking_compat["supportsTools"] is False
    assert thinking_compat["supportsReasoningEffort"] is False


@pytest.mark.asyncio
async def test_builds_the_openrouter_backed_arcee_ai_model_catalog() -> None:
    captured = create_captured_plugin_registration(id="arcee")
    arcee_plugin.register(captured.api)
    provider = captured.providers[0]

    catalog_provider = await _run_single_provider_catalog(
        provider,
        resolve_provider_api_key=lambda provider_id=None: (
            {"apiKey": "sk-or-test"} if provider_id == "openrouter" else {"apiKey": None}
        ),
    )

    assert catalog_provider["baseUrl"] == OPENROUTER_BASE_URL
    assert [model["id"] for model in catalog_provider["models"]] == [
        "arcee/trinity-mini",
        "arcee/trinity-large-preview",
        "arcee/trinity-large-thinking",
    ]
    thinking_compat = next(
        model["compat"]
        for model in catalog_provider["models"]
        if model["id"] == "arcee/trinity-large-thinking"
    )
    assert thinking_compat["supportsTools"] is False
    assert thinking_compat["supportsReasoningEffort"] is False


def test_normalizes_arcee_openrouter_models_to_vendor_prefixed_runtime_ids() -> None:
    open_router_model = normalize_arcee_resolved_model(
        {
            "provider": "arcee",
            "id": "trinity-large-thinking",
            "name": "Trinity Large Thinking",
            "api": "openai-completions",
            "baseUrl": OPENROUTER_BASE_URL,
        }
    )
    assert open_router_model is not None
    assert open_router_model["id"] == "arcee/trinity-large-thinking"

    assert (
        normalize_arcee_resolved_model(
            {
                "provider": "arcee",
                "id": "trinity-large-thinking",
                "name": "Trinity Large Thinking",
                "api": "openai-completions",
                "baseUrl": ARCEE_BASE_URL,
            }
        )
        is None
    )


def test_canonicalizes_stale_openrouter_config_and_transport_metadata() -> None:
    captured = create_captured_plugin_registration(id="arcee")
    arcee_plugin.register(captured.api)
    provider = captured.providers[0]

    normalized_config = provider["normalizeConfig"](
        {
            "provider": "arcee",
            "providerConfig": {
                "api": "openai-completions",
                "baseUrl": "https://openrouter.ai/v1/",
                "models": [],
            },
        }
    )
    assert normalized_config is not None
    assert normalized_config["baseUrl"] == OPENROUTER_BASE_URL

    normalized_model = normalize_arcee_resolved_model(
        {
            "provider": "arcee",
            "id": "trinity-large-thinking",
            "name": "Trinity Large Thinking",
            "api": "openai-completions",
            "baseUrl": "https://openrouter.ai/v1",
        }
    )
    assert normalized_model is not None
    assert normalized_model["id"] == "arcee/trinity-large-thinking"
    assert normalized_model["baseUrl"] == OPENROUTER_BASE_URL

    normalized_transport = provider["normalizeTransport"](
        {
            "provider": "arcee",
            "api": "openai-completions",
            "baseUrl": "https://openrouter.ai/v1",
        }
    )
    assert normalized_transport == {
        "api": "openai-completions",
        "baseUrl": OPENROUTER_BASE_URL,
    }


def test_exposes_static_catalog_helpers() -> None:
    assert ARCEE_BASE_URL == "https://api.arcee.ai/api/v1"
    assert OPENROUTER_BASE_URL == "https://openrouter.ai/api/v1"
    assert ARCEE_DEFAULT_MODEL_REF == "arcee/trinity-large-thinking"
    assert ARCEE_OPENROUTER_DEFAULT_MODEL_REF == "arcee/trinity-large-thinking"
    assert len(ARCEE_MODEL_CATALOG) == 3
    assert len(build_arcee_catalog_models()) == 3
    assert len(build_arcee_open_router_catalog_models()) == 3


def test_build_arcee_model_definition_adds_openai_completions_api() -> None:
    model = ARCEE_MODEL_CATALOG[2]
    defined = build_arcee_model_definition(model)

    assert defined["id"] == model["id"]
    assert defined["api"] == "openai-completions"
    assert defined["compat"] == model["compat"]


def test_build_arcee_provider_and_openrouter_provider() -> None:
    direct = build_arcee_provider()
    open_router = build_arcee_open_router_provider()

    assert direct["baseUrl"] == ARCEE_BASE_URL
    assert open_router["baseUrl"] == OPENROUTER_BASE_URL
    assert [model["id"] for model in direct["models"]] == [
        "trinity-mini",
        "trinity-large-preview",
        "trinity-large-thinking",
    ]
    assert [model["id"] for model in open_router["models"]] == [
        "arcee/trinity-mini",
        "arcee/trinity-large-preview",
        "arcee/trinity-large-thinking",
    ]


def test_apply_arcee_config_seeds_direct_provider_defaults() -> None:
    result = apply_arcee_config({})
    provider = result.get("models", {}).get("providers", {}).get("arcee")

    assert provider == {
        "baseUrl": ARCEE_BASE_URL,
        "api": "openai-completions",
        "models": build_arcee_catalog_models(),
    }


def test_normalize_arcee_open_router_base_url_and_model_id_helpers() -> None:
    assert normalize_arcee_open_router_base_url("https://openrouter.ai/v1/") == OPENROUTER_BASE_URL
    assert normalize_arcee_open_router_base_url(OPENROUTER_BASE_URL) == OPENROUTER_BASE_URL
    assert normalize_arcee_open_router_base_url("https://api.arcee.ai/api/v1") is None
    assert normalize_arcee_open_router_base_url(None) is None

    assert to_arcee_open_router_model_id("trinity-mini") == "arcee/trinity-mini"
    assert to_arcee_open_router_model_id("arcee/trinity-mini") == "arcee/trinity-mini"
    assert to_arcee_open_router_model_id("  ") == ""


@pytest.mark.asyncio
async def test_resolve_arcee_catalog_prefers_direct_key_over_openrouter() -> None:
    direct = await resolve_arcee_catalog(
        {
            "resolveProviderApiKey": lambda provider_id=None: (
                {"apiKey": "direct-key"} if provider_id == "arcee" else {"apiKey": "sk-or-test"}
            ),
        }
    )
    assert direct is not None
    assert direct["provider"]["baseUrl"] == ARCEE_BASE_URL
    assert direct["provider"]["apiKey"] == "direct-key"

    open_router = await resolve_arcee_catalog(
        {
            "resolveProviderApiKey": lambda provider_id=None: (
                {"apiKey": "sk-or-test"} if provider_id == "openrouter" else {"apiKey": None}
            ),
        }
    )
    assert open_router is not None
    assert open_router["provider"]["baseUrl"] == OPENROUTER_BASE_URL
