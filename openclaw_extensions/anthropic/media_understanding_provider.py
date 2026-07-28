from __future__ import annotations

from typing import Any

from openclaw.plugin_sdk.media_understanding import (
    describe_image_with_model,
    describe_images_with_model,
)

anthropic_media_understanding_provider: dict[str, Any] = {
    "id": "anthropic",
    "capabilities": ["image"],
    "defaultModels": {"image": "claude-opus-4-8"},
    "autoPriority": {"image": 20},
    "nativeDocumentInputs": ["pdf"],
    "describeImage": describe_image_with_model,
    "describeImages": describe_images_with_model,
}