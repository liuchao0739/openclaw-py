"""Tests for model catalog ref helpers."""

from __future__ import annotations

from openclaw_packages.model_catalog_core import (
    build_model_catalog_merge_key,
    build_model_catalog_ref,
)


def test_normalizes_provider_ids_without_lowercasing_model_ids_in_refs() -> None:
    assert build_model_catalog_ref("OpenAI", "GPT-5.4") == "openai/GPT-5.4"
    assert build_model_catalog_merge_key("OpenAI", "GPT-5.4") == "openai::gpt-5.4"
