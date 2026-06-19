"""Plugin manifest models and loader."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from openclaw.plugin_sdk import PLUGIN_MANIFEST_FILENAME


class PluginActivation(BaseModel):
    on_startup: bool = Field(default=False, alias="onStartup")

    model_config = {"populate_by_name": True}


class PluginManifest(BaseModel):
    id: str
    activation: PluginActivation | None = None
    channels: list[str] = Field(default_factory=list)
    channel_env_vars: dict[str, list[str]] = Field(default_factory=dict, alias="channelEnvVars")
    config_schema: dict[str, Any] = Field(default_factory=dict, alias="configSchema")

    model_config = {"populate_by_name": True, "extra": "allow"}


def load_plugin_manifest(path: str | Path) -> PluginManifest:
    manifest_path = Path(path)
    if manifest_path.is_dir():
        manifest_path = manifest_path / PLUGIN_MANIFEST_FILENAME
    raw = json.loads(manifest_path.read_text(encoding="utf-8"))
    return PluginManifest.model_validate(raw)
