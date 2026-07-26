"""Fireworks provider model/runtime integration."""

from __future__ import annotations

import copy
import json
from pathlib import Path

from openclaw.plugin_sdk.provider_catalog_shared import (
    ModelDefinitionConfig,
    ModelProviderConfig,
    build_manifest_model_provider_config,
)

_MANIFEST_PATH = Path(__file__).resolve().parent / "openclaw.plugin.json"
_MANIFEST = json.loads(_MANIFEST_PATH.read_text(encoding="utf-8"))
_FIREWORKS_MANIFEST_CATALOG = _MANIFEST["modelCatalog"]["providers"]["fireworks"]

_FIREWORKS_MANIFEST_PROVIDER = build_manifest_model_provider_config(
    provider_id="fireworks",
    catalog=_FIREWORKS_MANIFEST_CATALOG,
)

FIREWORKS_BASE_URL = _FIREWORKS_MANIFEST_PROVIDER["baseUrl"]
FIREWORKS_DEFAULT_MODEL_ID = "accounts/fireworks/routers/kimi-k2p5-turbo"


def _require_fireworks_manifest_model(model_id: str) -> ModelDefinitionConfig:
    for model in _FIREWORKS_MANIFEST_PROVIDER["models"]:
        if model.get("id") == model_id:
            return model
    raise ValueError(f"Missing Fireworks modelCatalog row {model_id}")


_FIREWORKS_DEFAULT_MODEL = _require_fireworks_manifest_model(FIREWORKS_DEFAULT_MODEL_ID)

FIREWORKS_DEFAULT_CONTEXT_WINDOW = _FIREWORKS_DEFAULT_MODEL["contextWindow"]
FIREWORKS_DEFAULT_MAX_TOKENS = _FIREWORKS_DEFAULT_MODEL["maxTokens"]


def is_fireworks_catalog_model_id(model_id: str) -> bool:
    return any(model.get("id") == model_id for model in _FIREWORKS_MANIFEST_PROVIDER["models"])


def build_fireworks_catalog_models() -> list[ModelDefinitionConfig]:
    return copy.deepcopy(_FIREWORKS_MANIFEST_PROVIDER["models"])


def build_fireworks_provider() -> ModelProviderConfig:
    return build_manifest_model_provider_config(
        provider_id="fireworks",
        catalog=_FIREWORKS_MANIFEST_CATALOG,
    )
