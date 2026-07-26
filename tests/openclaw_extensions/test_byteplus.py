"""Tests for the BytePlus provider extension."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from openclaw.plugin_sdk.plugin_test_runtime import create_captured_plugin_registration
from openclaw_extensions.byteplus.index import default as byteplus_plugin
from openclaw_extensions.byteplus.models import (
    BYTEPLUS_CODING_MODEL_CATALOG,
    BYTEPLUS_MODEL_CATALOG,
)

_MANIFEST_PATH = (
    Path(__file__).resolve().parents[2]
    / "openclaw_extensions"
    / "byteplus"
    / "openclaw.plugin.json"
)


def _read_manifest() -> dict[str, Any]:
    return json.loads(_MANIFEST_PATH.read_text(encoding="utf-8"))


def test_augments_the_catalog_with_bundled_standard_and_plan_models() -> None:
    captured = create_captured_plugin_registration(id="byteplus")
    byteplus_plugin.register(captured.api)
    assert captured.providers, "expected BytePlus provider registration"
    provider = captured.providers[0]
    augment_model_catalog = provider.get("augmentModelCatalog")
    assert augment_model_catalog is not None

    entries = augment_model_catalog({"env": {}, "entries": []})

    standard_entry = next(
        (
            entry
            for entry in entries
            if entry["provider"] == "byteplus" and entry["id"] == BYTEPLUS_MODEL_CATALOG[0]["id"]
        ),
        None,
    )
    assert standard_entry is not None
    assert standard_entry["name"] == BYTEPLUS_MODEL_CATALOG[0]["name"]
    assert standard_entry["reasoning"] == BYTEPLUS_MODEL_CATALOG[0].get("reasoning")
    assert standard_entry["input"] == list(BYTEPLUS_MODEL_CATALOG[0]["input"])
    assert standard_entry["contextWindow"] == BYTEPLUS_MODEL_CATALOG[0]["contextWindow"]

    plan_entry = next(
        (
            entry
            for entry in entries
            if entry["provider"] == "byteplus-plan"
            and entry["id"] == BYTEPLUS_CODING_MODEL_CATALOG[0]["id"]
        ),
        None,
    )
    assert plan_entry is not None
    assert plan_entry["name"] == BYTEPLUS_CODING_MODEL_CATALOG[0]["name"]
    assert plan_entry["reasoning"] == BYTEPLUS_CODING_MODEL_CATALOG[0].get("reasoning")
    assert plan_entry["input"] == list(BYTEPLUS_CODING_MODEL_CATALOG[0]["input"])
    assert plan_entry["contextWindow"] == BYTEPLUS_CODING_MODEL_CATALOG[0]["contextWindow"]


def test_declares_its_coding_provider_auth_alias_in_the_manifest() -> None:
    plugin_json = _read_manifest()
    assert plugin_json["providerAuthAliases"] == {
        "byteplus-plan": "byteplus",
    }


def test_keeps_kimi_catalog_metadata_aligned_with_provider_capabilities() -> None:
    standard_kimi = next(
        (entry for entry in BYTEPLUS_MODEL_CATALOG if entry["id"] == "kimi-k2-5-260127"),
        None,
    )
    plan_kimi = next(
        (entry for entry in BYTEPLUS_CODING_MODEL_CATALOG if entry["id"] == "kimi-k2.5"),
        None,
    )
    thinking_kimi = next(
        (entry for entry in BYTEPLUS_CODING_MODEL_CATALOG if entry["id"] == "kimi-k2-thinking"),
        None,
    )

    for entry in (standard_kimi, plan_kimi, thinking_kimi):
        assert entry is not None
        assert entry.get("reasoning") is True
        assert entry["maxTokens"] == 32768
        assert entry["cost"]["input"] == 0.6
        assert entry["cost"]["output"] == 2.5
        assert entry["cost"]["cacheRead"] == 0.12
        assert entry["cost"]["cacheWrite"] == 0
