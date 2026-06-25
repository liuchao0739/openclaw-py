"""Tests for channels root — chat type, sender label, thread binding, progress lines."""

from __future__ import annotations

from openclaw.channels.chat_type import normalize_chat_type
from openclaw.channels.progress_draft_lines import remove_channel_progress_draft_line
from openclaw.channels.sender_label import resolve_sender_label
from openclaw.channels.thread_binding_id import (
    resolve_thread_binding_conversation_id_from_binding_id,
)


class TestChatType:
    def test_direct(self):
        assert normalize_chat_type("direct") == "direct"
        assert normalize_chat_type("DM") == "direct"
        assert normalize_chat_type("dm") == "direct"

    def test_group(self):
        assert normalize_chat_type("group") == "group"

    def test_channel(self):
        assert normalize_chat_type("channel") == "channel"

    def test_unknown(self):
        assert normalize_chat_type("custom") is None
        assert normalize_chat_type("") is None
        assert normalize_chat_type(None) is None


class TestSenderLabel:
    def test_name_with_id(self):
        assert resolve_sender_label(name="Alice", id="123") == "Alice (123)"

    def test_username_only(self):
        assert resolve_sender_label(username="alice") == "alice"

    def test_id_only(self):
        assert resolve_sender_label(id="123") == "123"

    def test_name_equals_id(self):
        assert resolve_sender_label(name="123", id="123") == "123"

    def test_all_empty(self):
        assert resolve_sender_label() is None

    def test_e164_fallback(self):
        assert resolve_sender_label(e164="+1234567890") == "+1234567890"

    def test_tag(self):
        assert resolve_sender_label(tag="@alice") == "@alice"


class TestThreadBindingId:
    def test_valid_binding(self):
        result = resolve_thread_binding_conversation_id_from_binding_id("acc1", "acc1:conv-123")
        assert result == "conv-123"

    def test_wrong_prefix(self):
        result = resolve_thread_binding_conversation_id_from_binding_id("acc1", "acc2:conv-123")
        assert result is None

    def test_empty(self):
        assert resolve_thread_binding_conversation_id_from_binding_id("acc1", None) is None
        assert resolve_thread_binding_conversation_id_from_binding_id("acc1", "") is None

    def test_no_conversation_id(self):
        assert resolve_thread_binding_conversation_id_from_binding_id("acc1", "acc1:") is None


class TestProgressDraftLines:
    def test_remove_keyed_line(self):
        lines = [
            {"id": "progress1", "text": "working"},
            {"id": "progress2", "text": "done"},
            "plain text line",
        ]
        result = remove_channel_progress_draft_line(lines, "progress1")
        assert len(result) == 2
        assert result[0]["id"] == "progress2"

    def test_no_removal_returns_same_list(self):
        lines = [{"id": "p1", "text": "x"}]
        result = remove_channel_progress_draft_line(lines, "nonexistent")
        assert result is lines

    def test_empty_id_returns_same(self):
        lines = [{"id": "p1"}]
        assert remove_channel_progress_draft_line(lines, "") is lines

    def test_preserves_plain_text(self):
        lines = ["plain", {"id": "p1", "text": "structured"}]
        result = remove_channel_progress_draft_line(lines, "p1")
        assert result == ["plain"]
