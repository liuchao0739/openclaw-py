"""Tests for the GMI provider extension."""

from __future__ import annotations

from openclaw_extensions.gmi.models import (
    GMI_BASE_URL,
    GMI_DEFAULT_MODEL_REF,
    GMI_MODEL_CATALOG,
    build_gmi_model_definition,
)
from openclaw_extensions.gmi.provider_catalog import build_gmi_provider


def test_registers_gmi_cloud_as_openai_compatible_provider() -> None:
    provider = build_gmi_provider()

    assert provider["baseUrl"] == "https://api.gmi-serving.com/v1"
    assert provider["api"] == "openai-completions"
    model_ids = [model["id"] for model in provider["models"]]
    assert "google/gemini-3.1-flash-lite" in model_ids
    assert all(model.get("api") == "openai-completions" for model in provider["models"])


def test_gmi_manifest_constants() -> None:
    assert GMI_BASE_URL == "https://api.gmi-serving.com/v1"
    assert GMI_DEFAULT_MODEL_REF == "gmi/google/gemini-3.1-flash-lite"
    assert len(GMI_MODEL_CATALOG) == 6
    assert {model["id"] for model in GMI_MODEL_CATALOG} == {
        "zai-org/GLM-5.1-FP8",
        "deepseek-ai/DeepSeek-V3.2",
        "moonshotai/Kimi-K2.5",
        "google/gemini-3.1-flash-lite",
        "anthropic/claude-sonnet-4.6",
        "openai/gpt-5.4",
    }


def test_build_gmi_model_definition_adds_openai_completions_api() -> None:
    model = GMI_MODEL_CATALOG[0]
    defined = build_gmi_model_definition(model)

    assert defined["id"] == model["id"]
    assert defined["api"] == "openai-completions"
    assert defined["name"] == model["name"]
