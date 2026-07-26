"""Cohere model catalog helpers derived from the plugin manifest."""

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
_COHERE_MANIFEST_CATALOG = _MANIFEST["modelCatalog"]["providers"]["cohere"]

COHERE_BASE_URL = _COHERE_MANIFEST_CATALOG["baseUrl"]
COHERE_MODEL_CATALOG: list[dict[str, Any]] = _COHERE_MANIFEST_CATALOG["models"]


def build_cohere_catalog_models() -> list[ModelDefinitionConfig]:
    return build_manifest_model_provider_config(
        provider_id="cohere",
        catalog=_COHERE_MANIFEST_CATALOG,
    )["models"]


def build_cohere_model_definition(model: dict[str, Any]) -> ModelDefinitionConfig:
    return build_manifest_model_provider_config(
        provider_id="cohere",
        catalog={**_COHERE_MANIFEST_CATALOG, "models": [model]},
    )["models"][0]
