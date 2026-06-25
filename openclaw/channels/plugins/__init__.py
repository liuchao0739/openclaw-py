"""Channel plugin root — capabilities, status, action gates, media limits, TTS."""

from openclaw.channels.plugins.account_action_gate import create_account_action_gate
from openclaw.channels.plugins.channel_id_types import ChannelId
from openclaw.channels.plugins.configured_binding_builtins import (
    ensure_configured_binding_builtins_registered,
    get_configured_binding_consumers,
    register_configured_binding_consumer,
)
from openclaw.channels.plugins.media_limits import resolve_channel_media_max_bytes
from openclaw.channels.plugins.message_capabilities import CHANNEL_MESSAGE_CAPABILITIES
from openclaw.channels.plugins.status_state import format_channel_status_state
from openclaw.channels.plugins.tts_capabilities import resolve_channel_tts_voice_delivery

__all__ = [
    "CHANNEL_MESSAGE_CAPABILITIES",
    "ChannelId",
    "create_account_action_gate",
    "ensure_configured_binding_builtins_registered",
    "format_channel_status_state",
    "get_configured_binding_consumers",
    "register_configured_binding_consumer",
    "resolve_channel_media_max_bytes",
    "resolve_channel_tts_voice_delivery",
]
