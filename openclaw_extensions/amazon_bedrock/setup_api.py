from __future__ import annotations

from openclaw.plugin_sdk.plugin_entry import define_plugin_entry
from openclaw_extensions.amazon_bedrock.config_api import (
    migrate_amazon_bedrock_legacy_config,
)
from openclaw_extensions.amazon_bedrock.discovery_shared import (
    resolve_bedrock_config_api_key,
)


default = define_plugin_entry(
    id="amazon-bedrock",
    name="Amazon Bedrock Setup",
    description="Lightweight Amazon Bedrock setup hooks",
    register=lambda api: _register(api),
)


def _register(api) -> None:
    api.register_provider({
        "id": "amazon-bedrock",
        "label": "Amazon Bedrock",
        "auth": [],
        "resolveConfigApiKey": lambda ctx: resolve_bedrock_config_api_key(ctx.get("env")),
    })
    api.register_config_migration(lambda config: migrate_amazon_bedrock_legacy_config(config))


__all__ = ["default"]