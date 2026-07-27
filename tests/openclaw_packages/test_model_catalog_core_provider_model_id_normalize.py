"""Tests for provider model id normalization helpers."""

from __future__ import annotations

from openclaw_packages.model_catalog_core import normalize_google_preview_model_id


def test_routes_bare_gemini_3_pro_to_current_gemini_3_1_pro_preview() -> None:
    assert normalize_google_preview_model_id("gemini-3-pro") == "gemini-3.1-pro-preview"
    assert normalize_google_preview_model_id("gemini-3-pro-preview") == "gemini-3.1-pro-preview"
    assert normalize_google_preview_model_id("gemini-3.1-pro") == "gemini-3.1-pro-preview"


def test_routes_provider_prefixed_gemini_3_pro_to_current_gemini_3_1_pro_preview() -> None:
    assert normalize_google_preview_model_id("google/gemini-3-pro-preview") == (
        "google/gemini-3.1-pro-preview"
    )


def test_does_not_rewrite_already_current_gemini_replacement_ids() -> None:
    assert normalize_google_preview_model_id("gemini-3.1-pro-preview") == "gemini-3.1-pro-preview"
    assert normalize_google_preview_model_id("gemini-2.5-flash") == "gemini-2.5-flash"


def test_maps_deprecated_flash_lite_preview_to_ga_flash_lite() -> None:
    assert normalize_google_preview_model_id("gemini-3.1-flash-lite-preview") == (
        "gemini-3.1-flash-lite"
    )
    assert normalize_google_preview_model_id("google/gemini-3.1-flash-lite-preview") == (
        "google/gemini-3.1-flash-lite"
    )


def test_does_not_rewrite_stable_ga_flash_lite() -> None:
    assert normalize_google_preview_model_id("gemini-3.1-flash-lite") == "gemini-3.1-flash-lite"


def test_routes_gemma_4_26b_shorthand_to_google_canonical_api_id() -> None:
    assert normalize_google_preview_model_id("gemma-4-26b") == "gemma-4-26b-a4b-it"
    assert normalize_google_preview_model_id("google/gemma-4-26b") == "google/gemma-4-26b-a4b-it"
