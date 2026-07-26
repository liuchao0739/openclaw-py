"""Tests for handleDiscordMessageAction."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, Mock, patch

import pytest

from openclaw.agents.tools.common import ToolInputError
from openclaw_extensions.discord.src.actions.handle_action import handle_discord_message_action
from openclaw_extensions.discord.src.inbound_event_delivery import (
    begin_discord_inbound_event_delivery_correlation,
    reset_discord_inbound_event_delivery_for_tests,
)


def _discord_config(actions: dict[str, bool] | None = None) -> dict[str, Any]:
    return {
        "channels": {
            "discord": {
                "token": "tok",
                **({"actions": actions} if actions else {}),
            }
        }
    }


@pytest.fixture(autouse=True)
def _reset_delivery_registry() -> None:
    reset_discord_inbound_event_delivery_for_tests()


@pytest.mark.asyncio
async def test_timeout_uses_trusted_requester_sender_id() -> None:
    handle_action = AsyncMock(return_value={"content": [], "details": {"ok": True}})
    cfg = _discord_config({"moderation": True})
    with patch(
        "openclaw_extensions.discord.src.actions.handle_action_guild_admin.handle_discord_action",
        handle_action,
    ):
        await handle_discord_message_action(
            {
                "action": "timeout",
                "params": {
                    "guildId": "guild-1",
                    "userId": "user-2",
                    "durationMin": 5,
                    "senderUserId": "spoofed-admin-id",
                },
                "cfg": cfg,
                "requesterSenderId": "trusted-sender-id",
                "toolContext": {"currentChannelProvider": "discord"},
            }
        )
    handle_action.assert_awaited_once()
    payload = handle_action.await_args.args[0]
    assert payload["senderUserId"] == "trusted-sender-id"


@pytest.mark.asyncio
async def test_rejects_fractional_moderation_duration() -> None:
    handle_action = AsyncMock()
    cfg = _discord_config({"moderation": True})
    with (
        patch(
            "openclaw_extensions.discord.src.actions.handle_action_guild_admin.handle_discord_action",
            handle_action,
        ),
        pytest.raises(ToolInputError, match="durationMin must be a non-negative integer"),
    ):
        await handle_discord_message_action(
            {
                "action": "timeout",
                "params": {
                    "guildId": "guild-1",
                    "userId": "user-2",
                    "durationMin": 5.5,
                },
                "cfg": cfg,
                "requesterSenderId": "trusted-sender-id",
                "toolContext": {"currentChannelProvider": "discord"},
            }
        )
    handle_action.assert_not_awaited()


@pytest.mark.asyncio
async def test_falls_back_to_tool_context_for_reactions() -> None:
    handle_action = AsyncMock(return_value={"content": [], "details": {"ok": True}})
    with patch(
        "openclaw_extensions.discord.src.actions.handle_action.handle_discord_action",
        handle_action,
    ):
        await handle_discord_message_action(
            {
                "action": "react",
                "params": {"channelId": "123", "emoji": "ok"},
                "cfg": _discord_config(),
                "toolContext": {"currentMessageId": "9001"},
            }
        )
    payload = handle_action.await_args.args[0]
    assert payload["messageId"] == "9001"


@pytest.mark.asyncio
async def test_notifies_inbound_event_delivery_after_send() -> None:
    handle_action = AsyncMock(return_value={"content": [], "details": {"ok": True}})
    mark_delivered = Mock()
    end = begin_discord_inbound_event_delivery_correlation(
        "agent:main:discord:channel:c1",
        {
            "outboundTo": "channel:c1",
            "outboundAccountId": "default",
            "markInboundEventDelivered": mark_delivered,
        },
        {"inboundEventKind": "room_event"},
    )
    try:
        with patch(
            "openclaw_extensions.discord.src.actions.handle_action.handle_discord_action",
            handle_action,
        ):
            await handle_discord_message_action(
                {
                    "action": "send",
                    "params": {"to": "channel:c1", "message": "hello"},
                    "cfg": _discord_config(),
                    "accountId": "default",
                    "sessionKey": "agent:main:discord:channel:c1",
                    "inboundEventKind": "room_event",
                }
            )
    finally:
        end()
    mark_delivered.assert_called_once()


@pytest.mark.asyncio
async def test_search_does_not_inject_session_channel_when_guild_id_explicit() -> None:
    handle_action = AsyncMock(return_value={"content": [], "details": {"ok": True}})
    with patch(
        "openclaw_extensions.discord.src.actions.handle_action_guild_admin.handle_discord_action",
        handle_action,
    ):
        await handle_discord_message_action(
            {
                "action": "search",
                "params": {"query": "guild-wide query", "guildId": "g1"},
                "cfg": _discord_config(),
                "toolContext": {
                    "currentChannelProvider": "discord",
                    "currentChannelId": "session-ch",
                },
            }
        )
    payload = handle_action.await_args.args[0]
    assert payload["guildId"] == "g1"
    assert "channelId" not in payload
    assert "channelIds" not in payload
