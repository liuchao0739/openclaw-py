"""BytePlus model catalog helpers derived from the plugin manifest."""

from __future__ import annotations

import json
from pathlib import Path

from openclaw.plugin_sdk.provider_catalog_shared import (
    ModelDefinitionConfig,
    build_manifest_model_provider_config,
)

_MANIFEST_PATH = Path(__file__).resolve().parent / "openclaw.plugin.json"
_MANIFEST = json.loads(_MANIFEST_PATH.read_text(encoding="utf-8"))

_BYTEPLUS_MANIFEST_PROVIDER = build_manifest_model_provider_config(
    provider_id="byteplus",
    catalog=_MANIFEST["modelCatalog"]["providers"]["byteplus"],
)

_BYTEPLUS_CODING_MANIFEST_PROVIDER = build_manifest_model_provider_config(
    provider_id="byteplus-plan",
    catalog=_MANIFEST["modelCatalog"]["providers"]["byteplus-plan"],
)

BYTEPLUS_BASE_URL = _BYTEPLUS_MANIFEST_PROVIDER["baseUrl"]
BYTEPLUS_CODING_BASE_URL = _BYTEPLUS_CODING_MANIFEST_PROVIDER["baseUrl"]

BYTEPLUS_MODEL_CATALOG: list[ModelDefinitionConfig] = _BYTEPLUS_MANIFEST_PROVIDER["models"]
BYTEPLUS_CODING_MODEL_CATALOG: list[ModelDefinitionConfig] = _BYTEPLUS_CODING_MANIFEST_PROVIDER[
    "models"
]


def build_byte_plus_model_definition(entry: ModelDefinitionConfig) -> ModelDefinitionConfig:
    """Clone one manifest model definition so callers can mutate safely."""
    cost = entry.get("cost")
    return {
        **entry,
        "input": list(entry["input"]),
        "cost": dict(cost) if isinstance(cost, dict) else {},
    }
