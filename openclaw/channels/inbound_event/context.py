"""Channel inbound event context builder.

Converts route, sender, command, media, and supplemental facts into finalized message context.
"""

from __future__ import annotations

from typing import Any

from openclaw.channels.inbound_event.media import build_channel_inbound_media_payload


def build_inbound_event_context(
    *,
    body: str | None = None,
    sender_id: str | None = None,
    sender_name: str | None = None,
    channel: str | None = None,
    chat_id: str | None = None,
    chat_type: str | None = None,
    agent_id: str | None = None,
    session_key: str | None = None,
    command_source: str | None = None,
    media_facts: list[dict[str, Any]] | None = None,
    was_mentioned: bool = False,
    has_control_command: bool = False,
) -> dict[str, Any]:
    """Build a finalized inbound event context from component facts."""
    context: dict[str, Any] = {
        "body": (body or "").strip(),
        "senderId": sender_id,
        "senderName": sender_name,
        "channel": channel,
        "chatId": chat_id,
        "chatType": chat_type,
        "agentId": agent_id,
        "sessionKey": session_key,
        "commandSource": command_source,
        "wasMentioned": was_mentioned,
        "hasControlCommand": has_control_command,
    }

    # Build media payload
    media_payload = build_channel_inbound_media_payload(media_facts)
    if media_payload:
        context["media"] = media_payload

    # Normalize newlines in body
    if context["body"]:
        context["body"] = context["body"].replace("\r\n", "\n").replace("\r", "\n")

    return context


def finalize_inbound_context(
    context: dict[str, Any],
    *,
    include_supplemental: bool = False,
    supplemental_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Finalize an inbound context with optional supplemental facts."""
    finalized = dict(context)

    if include_supplemental and supplemental_context:
        for key, value in supplemental_context.items():
            if key not in finalized:
                finalized[key] = value

    return finalized
