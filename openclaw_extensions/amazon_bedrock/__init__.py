from __future__ import annotations

from openclaw.plugin_sdk.plugin_entry import define_plugin_entry
from openclaw_extensions.amazon_bedrock.register_runtime import (
    register_amazon_bedrock_plugin,
)


default = define_plugin_entry(
    id="amazon-bedrock",
    name="Amazon Bedrock Provider",
    description="Bundled Amazon Bedrock provider policy plugin",
    register=lambda api: register_amazon_bedrock_plugin(api),
)


__all__ = ["default", "register_amazon_bedrock_plugin"]