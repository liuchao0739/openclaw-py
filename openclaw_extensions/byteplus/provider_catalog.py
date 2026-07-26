"""BytePlus model provider builders backed by the plugin manifest catalog."""

from __future__ import annotations

import json
from pathlib import Path

from openclaw.plugin_sdk.provider_catalog_shared import (
    ModelProviderConfig,
    build_manifest_model_provider_config,
)

_MANIFEST_PATH = Path(__file__).resolve().parent / "openclaw.plugin.json"
_MANIFEST = json.loads(_MANIFEST_PATH.read_text(encoding="utf-8"))


def build_byte_plus_provider() -> ModelProviderConfig:
    """Build the standard BytePlus model provider config."""
    return build_manifest_model_provider_config(
        provider_id="byteplus",
        catalog=_MANIFEST["modelCatalog"]["providers"]["byteplus"],
    )


def build_byte_plus_coding_provider() -> ModelProviderConfig:
    """Build the BytePlus Plan coding-provider config."""
    return build_manifest_model_provider_config(
        provider_id="byteplus-plan",
        catalog=_MANIFEST["modelCatalog"]["providers"]["byteplus-plan"],
    )
