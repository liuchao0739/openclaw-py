from __future__ import annotations

from openclaw_extensions.googlechat.runtime_api import (
    DEFAULT_ACCOUNT_ID,
    GoogleChatConfigSchema,
    OpenClawConfig,
    build_channel_config_schema,
    chunk_text_for_outbound,
    load_outbound_media_from_url,
    missing_target_error,
    read_remote_media_buffer,
    resolve_channel_media_max_bytes,
)
from openclaw_extensions.googlechat.src.accounts import (
    GoogleChatConfigAccessorAccount,
    ResolvedGoogleChatAccount,
    list_google_chat_account_ids,
    resolve_default_google_chat_account_id,
    resolve_google_chat_account,
    resolve_google_chat_config_accessor_account,
)
from openclaw_extensions.googlechat.src.targets import (
    is_google_chat_space_target,
    is_google_chat_user_target,
    normalize_google_chat_target,
    resolve_google_chat_outbound_space,
)

__all__ = [
    "build_channel_config_schema",
    "chunk_text_for_outbound",
    "DEFAULT_ACCOUNT_ID",
    "read_remote_media_buffer",
    "GoogleChatConfigSchema",
    "load_outbound_media_from_url",
    "missing_target_error",
    "PAIRING_APPROVED_MESSAGE",
    "resolve_channel_media_max_bytes",
    "ChannelMessageActionAdapter",
    "ChannelMessageActionName",
    "ChannelStatusIssue",
    "OpenClawConfig",
    "GoogleChatConfigAccessorAccount",
    "list_google_chat_account_ids",
    "resolve_google_chat_config_accessor_account",
    "resolve_default_google_chat_account_id",
    "resolve_google_chat_account",
    "ResolvedGoogleChatAccount",
    "is_google_chat_space_target",
    "is_google_chat_user_target",
    "normalize_google_chat_target",
    "resolve_google_chat_outbound_space",
]