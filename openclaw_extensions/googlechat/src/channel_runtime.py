from __future__ import annotations

from openclaw_extensions.googlechat.src.api import (
    probe_google_chat as probe_google_chat_impl,
    send_google_chat_message as send_google_chat_message_impl,
    upload_google_chat_attachment as upload_google_chat_attachment_impl,
)
from openclaw_extensions.googlechat.src.monitor import (
    resolve_google_chat_webhook_path as resolve_google_chat_webhook_path_impl,
    start_google_chat_monitor as start_google_chat_monitor_impl,
)

google_chat_channel_runtime = {
    "probeGoogleChat": probe_google_chat_impl,
    "sendGoogleChatMessage": send_google_chat_message_impl,
    "uploadGoogleChatAttachment": upload_google_chat_attachment_impl,
    "resolveGoogleChatWebhookPath": resolve_google_chat_webhook_path_impl,
    "startGoogleChatMonitor": start_google_chat_monitor_impl,
}

__all__ = ["google_chat_channel_runtime"]