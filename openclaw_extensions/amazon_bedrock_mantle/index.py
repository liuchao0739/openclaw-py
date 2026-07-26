"""Amazon Bedrock Mantle plugin entry."""

from __future__ import annotations

from openclaw.plugin_sdk.plugin_entry import OpenClawPluginApi, define_plugin_entry
from openclaw_extensions.amazon_bedrock_mantle.register_sync_runtime import (
    register_bedrock_mantle_plugin,
)


def _register(api: OpenClawPluginApi) -> None:
    register_bedrock_mantle_plugin(api)


default = define_plugin_entry(
    id="amazon-bedrock-mantle",
    name="Amazon Bedrock Mantle Provider",
    description="Bundled Amazon Bedrock Mantle (OpenAI-compatible) provider plugin",
    register=_register,
)
