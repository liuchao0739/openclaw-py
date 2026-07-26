"""DeepSeek model catalog helpers derived from the plugin manifest."""

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
_DEEPSEEK_MANIFEST_CATALOG = _MANIFEST["modelCatalog"]["providers"]["deepseek"]

_DEEPSEEK_MANIFEST_PROVIDER = build_manifest_model_provider_config(
    provider_id="deepseek",
    catalog=_DEEPSEEK_MANIFEST_CATALOG,
)

DEEPSEEK_BASE_URL = _DEEPSEEK_MANIFEST_PROVIDER["baseUrl"]
DEEPSEEK_MODEL_CATALOG: list[ModelDefinitionConfig] = _DEEPSEEK_MANIFEST_PROVIDER["models"]

_DEEPSEEK_V4_MODEL_IDS = frozenset({"deepseek-v4-flash", "deepseek-v4-pro"})


def build_deep_seek_model_definition(
    model: ModelDefinitionConfig,
) -> ModelDefinitionConfig:
    return {
        **model,
        "api": "openai-completions",
    }


def is_deep_seek_v4_model_id(model_id: str) -> bool:
    return model_id.lower() in _DEEPSEEK_V4_MODEL_IDS


def is_deep_seek_v4_model_ref(model: dict[str, Any]) -> bool:
    model_id = model.get("id")
    return (
        model.get("provider") == "deepseek"
        and isinstance(model_id, str)
        and is_deep_seek_v4_model_id(model_id)
    )
