"""Channel TTS voice capability resolver."""

from __future__ import annotations

from typing import Any


def resolve_channel_tts_voice_delivery(
    channel: str | None,
) -> dict[str, Any] | None:
    """Read channel-advertised voice delivery support for prompt and runtime routing."""
    if not channel:
        return None
    channel_id = channel.strip().lower()
    if not channel_id:
        return None
    try:
        from openclaw.channels.plugins.registry import get_channel_plugin

        plugin = get_channel_plugin(channel_id)
        if plugin:
            capabilities = plugin.get("capabilities", {})
            tts = capabilities.get("tts", {})
            return tts.get("voice")
    except Exception:
        pass
    return None
