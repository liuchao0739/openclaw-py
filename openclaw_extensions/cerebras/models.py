"""Cerebras model catalog helpers derived from the plugin manifest."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from openclaw.plugin_sdk.provider_catalog_shared import (
    ModelDefinitionConfig,
    build_manifest_model_provider_config,
)

_MANIFEST_PATH = Path(__file__).resolve().parent / "openclaw.plugin.json"
_MANIFEST = json.loads(_MANIFEST_PATH.read_text(encoding="utf-8"))
_CEREBRAS_MANIFEST_CATALOG = _MANIFEST["modelCatalog"]["providers"]["cerebras"]

CEREBRAS_BASE_URL = _CEREBRAS_MANIFEST_CATALOG["baseUrl"]
CEREBRAS_MODEL_CATALOG: list[dict[str, Any]] = _CEREBRAS_MANIFEST_CATALOG["models"]


def build_cerebras_catalog_models() -> list[ModelDefinitionConfig]:
    return build_manifest_model_provider_config(
        provider_id="cerebras",
        catalog=_CEREBRAS_MANIFEST_CATALOG,
    )["models"]


def build_cerebras_model_definition(model: dict[str, Any]) -> ModelDefinitionConfig:
    return build_manifest_model_provider_config(
        provider_id="cerebras",
        catalog={**_CEREBRAS_MANIFEST_CATALOG, "models": [model]},
    )["models"][0]
