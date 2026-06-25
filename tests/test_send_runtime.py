"""Tests for cli/send_runtime — channel outbound send."""

from __future__ import annotations

from openclaw.cli.send_runtime import create_channel_outbound_runtime_send


class TestChannelOutboundRuntimeSend:
    async def test_send_text_unavailable(self):
        runtime = create_channel_outbound_runtime_send("test", "Channel not available")
        try:
            await runtime["sendMessage"]("user1", "hello")
            assert False, "Should have raised"
        except RuntimeError as e:
            assert "Channel not available" in str(e)

    async def test_send_text_with_mock_adapter(self):
        """Test send_text path with a mock outbound adapter."""
        import openclaw.cli.send_runtime.channel_outbound_send as mod

        async def mock_load(channel_id: str):
            async def send_text(ctx):
                return {"messageId": "msg-1", "channel": channel_id, "to": ctx["to"]}
            return {"sendText": send_text}

        original = mod._load_channel_outbound_adapter
        mod._load_channel_outbound_adapter = mock_load
        try:
            runtime = create_channel_outbound_runtime_send("telegram", "unavailable")
            result = await runtime["sendMessage"]("user1", "hello", {"accountId": "acc1"})
            assert result["messageId"] == "msg-1"
            assert result["to"] == "user1"
        finally:
            mod._load_channel_outbound_adapter = original

    async def test_send_media_with_mock_adapter(self):
        """Test send_media path."""
        import openclaw.cli.send_runtime.channel_outbound_send as mod

        async def mock_load(channel_id: str):
            async def send_media(ctx):
                return {"messageId": "media-1", "mediaUrl": ctx["mediaUrl"]}
            return {"sendMedia": send_media, "sendText": lambda ctx: {}}

        original = mod._load_channel_outbound_adapter
        mod._load_channel_outbound_adapter = mock_load
        try:
            runtime = create_channel_outbound_runtime_send("telegram", "unavailable")
            result = await runtime["sendMessage"]("user1", "caption", {"mediaUrl": "https://example.com/img.png"})
            assert result["messageId"] == "media-1"
        finally:
            mod._load_channel_outbound_adapter = original
