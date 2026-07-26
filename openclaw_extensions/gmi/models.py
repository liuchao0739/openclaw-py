"""GMI plugin models behavior."""

from __future__ import annotations

import json
from pathlib import Path

from openclaw.plugin_sdk.provider_catalog_shared import (
    ModelDefinitionConfig,
    build_manifest_model_provider_config,
)

_MANIFEST_PATH = Path(__file__).resolve().parent / "openclaw.plugin.json"
_MANIFEST = json.loads(_MANIFEST_PATH.read_text(encoding="utf-8"))

_GMI_MANIFEST_PROVIDER = build_manifest_model_provider_config(
    provider_id="gmi",
    catalog=_MANIFEST["modelCatalog"]["providers"]["gmi"],
)

GMI_BASE_URL = _GMI_MANIFEST_PROVIDER["baseUrl"]
GMI_MODEL_CATALOG: list[ModelDefinitionConfig] = _GMI_MANIFEST_PROVIDER["models"]
GMI_DEFAULT_MODEL_REF = "gmi/google/gemini-3.1-flash-lite"


def build_gmi_model_definition(model: ModelDefinitionConfig) -> ModelDefinitionConfig:
    return {**model, "api": "openai-completions"}
