"""Runtime send adapter used by CLI send commands for channel plugins."""

from __future__ import annotations

from typing import Any


def _resolve_runtime_thread_id(opts: dict[str, Any]) -> str | int | None:
    return opts.get("messageThreadId") or opts.get("threadId") or opts.get("threadTs")


def _resolve_runtime_reply_to_id(opts: dict[str, Any]) -> str | None:
    raw = opts.get("replyToMessageId") or opts.get("replyToId")
    if raw is None:
        return None
    s = str(raw).strip()
    return s or None


async def _load_channel_outbound_adapter(channel_id: str) -> dict[str, Any] | None:
    """Load a channel outbound adapter. Deferred to plugins/outbound/load."""
    try:
        from openclaw.channels.plugins.outbound.load import load_outbound_plugin

        result = await load_outbound_plugin(channel_id)
        if result:
            return result.get("adapter")
    except Exception:
        pass
    return None


def _get_runtime_config() -> dict[str, Any]:
    """Get the runtime config. Deferred to config module."""
    try:
        from openclaw.config.config import get_runtime_config

        return get_runtime_config()
    except Exception:
        return {}


def create_channel_outbound_runtime_send(
    channel_id: str,
    unavailable_message: str,
) -> dict[str, Any]:
    """Create a send runtime that dispatches text, media, or rich blocks through a channel plugin."""

    async def send_message(
        to: str,
        text: str,
        opts: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        opts = opts or {}
        outbound = await _load_channel_outbound_adapter(channel_id)
        thread_id = _resolve_runtime_thread_id(opts)
        reply_to_id = _resolve_runtime_reply_to_id(opts)

        def build_context() -> dict[str, Any]:
            formatting = opts.get("formatting")
            if not formatting and opts.get("textMode") == "html":
                formatting = {"parseMode": "HTML"}
            return {
                "cfg": opts.get("cfg") or _get_runtime_config(),
                "to": to,
                "text": text,
                "mediaUrl": opts.get("mediaUrl"),
                "mediaAccess": opts.get("mediaAccess"),
                "mediaLocalRoots": opts.get("mediaLocalRoots"),
                "mediaReadFile": opts.get("mediaReadFile"),
                "accountId": opts.get("accountId"),
                "threadId": thread_id,
                "replyToId": reply_to_id,
                "silent": opts.get("silent"),
                "forceDocument": opts.get("forceDocument"),
                "formatting": formatting,
                "gifPlayback": opts.get("gifPlayback"),
                "gatewayClientScopes": opts.get("gatewayClientScopes"),
            }

        has_media = bool(opts.get("mediaUrl"))
        blocks = opts.get("blocks")

        if blocks and outbound and "sendPayload" in outbound:
            ctx = build_context()
            ctx["payload"] = {
                "text": text,
                "channelData": {channel_id: {"blocks": blocks}},
            }
            return await outbound["sendPayload"](ctx)

        if has_media and outbound and "sendMedia" in outbound:
            return await outbound["sendMedia"](build_context())

        if not outbound or "sendText" not in outbound:
            raise RuntimeError(unavailable_message)

        return await outbound["sendText"](build_context())

    return {"sendMessage": send_message}
