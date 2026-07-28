from __future__ import annotations

from openclaw_extensions.googlechat.config_api import (
    GoogleChatConfigSchema,
    build_channel_config_schema,
)

GoogleChatChannelConfigSchema = build_channel_config_schema(GoogleChatConfigSchema)

__all__ = ["GoogleChatChannelConfigSchema"]