from __future__ import annotations

from openclaw_extensions.googlechat.src.accounts import ResolvedGoogleChatAccount
from openclaw_extensions.googlechat.src.channel_base import create_google_chat_plugin_base

googlechat_setup_plugin = create_google_chat_plugin_base()

__all__ = ["googlechat_setup_plugin"]