"""Tests for channels/inbound_event — kind, classification, media, context."""

from __future__ import annotations

from openclaw.channels.inbound_event import (
    build_channel_inbound_media_payload,
    build_inbound_event_context,
    classify_channel_inbound_event,
    finalize_inbound_context,
    normalize_inbound_media_facts,
    resolve_unmentioned_group_inbound_policy,
)


class TestClassification:
    def test_default_policy_user_request(self):
        result = classify_channel_inbound_event()
        assert result == "user_request"

    def test_room_event_policy_with_group(self):
        result = classify_channel_inbound_event(
            conversation_kind="group",
            unmentioned_group_policy="room_event",
        )
        assert result == "room_event"

    def test_room_event_policy_with_mention(self):
        result = classify_channel_inbound_event(
            conversation_kind="group",
            unmentioned_group_policy="room_event",
            was_mentioned=True,
        )
        assert result == "user_request"

    def test_room_event_policy_with_control_command(self):
        result = classify_channel_inbound_event(
            conversation_kind="group",
            unmentioned_group_policy="room_event",
            has_control_command=True,
        )
        assert result == "user_request"

    def test_room_event_policy_with_native_command(self):
        result = classify_channel_inbound_event(
            conversation_kind="group",
            unmentioned_group_policy="room_event",
            command_source="native",
        )
        assert result == "user_request"

    def test_room_event_policy_with_abort(self):
        result = classify_channel_inbound_event(
            conversation_kind="group",
            unmentioned_group_policy="room_event",
            has_abort_request=True,
        )
        assert result == "user_request"

    def test_room_event_policy_with_direct_chat(self):
        result = classify_channel_inbound_event(
            conversation_kind="direct",
            unmentioned_group_policy="room_event",
        )
        assert result == "user_request"

    def test_resolve_policy_default(self):
        assert resolve_unmentioned_group_inbound_policy(None) == "user_request"

    def test_resolve_policy_from_config(self):
        cfg = {"messages": {"groupChat": {"unmentionedInbound": "room_event"}}}
        assert resolve_unmentioned_group_inbound_policy(cfg) == "room_event"


class TestMedia:
    def test_build_media_payload_empty(self):
        assert build_channel_inbound_media_payload(None) == []

    def test_build_media_payload(self):
        media = [{"mimeType": "image/png", "data": "base64data"}]
        result = build_channel_inbound_media_payload(media)
        assert len(result) == 1
        assert result[0]["type"] == "image"
        assert result[0]["mimeType"] == "image/png"

    def test_normalize_media_facts(self):
        raw = [{"mime_type": "image/jpeg", "url": "https://example.com/img.jpg"}]
        result = normalize_inbound_media_facts(raw)
        assert len(result) == 1
        assert result[0]["mimeType"] == "image/jpeg"
        assert result[0]["data"] == "https://example.com/img.jpg"


class TestContext:
    def test_build_context(self):
        ctx = build_inbound_event_context(
            body="hello world",
            sender_id="user1",
            channel="telegram",
            chat_type="direct",
        )
        assert ctx["body"] == "hello world"
        assert ctx["senderId"] == "user1"
        assert ctx["channel"] == "telegram"

    def test_build_context_normalizes_newlines(self):
        ctx = build_inbound_event_context(body="hello\r\nworld\rtest")
        assert ctx["body"] == "hello\nworld\ntest"

    def test_build_context_with_media(self):
        ctx = build_inbound_event_context(
            body="check this",
            media_facts=[{"mimeType": "image/png", "data": "abc"}],
        )
        assert "media" in ctx
        assert len(ctx["media"]) == 1

    def test_finalize_context(self):
        ctx = build_inbound_event_context(body="hello")
        finalized = finalize_inbound_context(
            ctx,
            include_supplemental=True,
            supplemental_context={"extraField": "value"},
        )
        assert finalized["extraField"] == "value"
        assert finalized["body"] == "hello"
