from __future__ import annotations

from typing import Any

from openclaw_extensions.googlechat.src.accounts import ResolvedGoogleChatAccount
from openclaw_extensions.googlechat.src.auth import GoogleChatAudienceType


class GoogleChatRuntimeEnv(dict):
    pass


class GoogleChatMonitorOptions(dict):
    pass


class WebhookTarget(dict):
    pass


__all__ = [
    "GoogleChatRuntimeEnv",
    "GoogleChatMonitorOptions",
    "WebhookTarget",
    "GoogleChatAudienceType",
]