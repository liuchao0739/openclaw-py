"""Auto-reply routing."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from openclaw.channels.base import InboundMessage, OutboundMessage

ReplyHandler = Callable[[InboundMessage], Awaitable[str] | str]


async def route_inbound(message: InboundMessage, handler: ReplyHandler) -> OutboundMessage:
    maybe = handler(message)
    reply_text = await maybe if hasattr(maybe, "__await__") else maybe
    return OutboundMessage(
        channel_id=message.channel_id,
        target_id=message.sender_id,
        text=reply_text,
    )
