"""Tests for auto_reply/reply root — inline whitespace, inbound text, delivery hints."""

from __future__ import annotations

from openclaw.auto_reply.reply.delivery_hints import (
    LEGACY_MESSAGE_TOOL_DELIVERY_HINTS,
    MESSAGE_TOOL_DELIVERY_HINTS,
    MESSAGE_TOOL_ONLY_DELIVERY_HINT,
)
from openclaw.auto_reply.reply.inbound_text import (
    normalize_inbound_text_newlines,
    sanitize_inbound_system_tags,
)
from openclaw.auto_reply.reply.reply_inline_whitespace import (
    collapse_inline_horizontal_whitespace,
)


class TestCollapseInlineWhitespace:
    def test_no_change(self):
        assert collapse_inline_horizontal_whitespace("hello world") == "hello world"

    def test_collapse_multiple_spaces(self):
        assert collapse_inline_horizontal_whitespace("hello    world") == "hello world"

    def test_collapse_tabs(self):
        assert collapse_inline_horizontal_whitespace("hello\t\tworld") == "hello world"

    def test_preserve_newlines(self):
        result = collapse_inline_horizontal_whitespace("hello\n\nworld")
        assert "\n\n" in result

    def test_mixed_whitespace(self):
        result = collapse_inline_horizontal_whitespace("hello \t world\nfoo")
        assert result == "hello world\nfoo"

    def test_empty(self):
        assert collapse_inline_horizontal_whitespace("") == ""


class TestNormalizeInboundNewlines:
    def test_crlf(self):
        assert normalize_inbound_text_newlines("hello\r\nworld") == "hello\nworld"

    def test_cr_only(self):
        assert normalize_inbound_text_newlines("hello\rworld") == "hello\nworld"

    def test_preserve_literal_backslash_n(self):
        text = r"C:\Work\nxxx\README.md"
        assert normalize_inbound_text_newlines(text) == text

    def test_no_change(self):
        assert normalize_inbound_text_newlines("hello\nworld") == "hello\nworld"

    def test_empty(self):
        assert normalize_inbound_text_newlines("") == ""

    def test_mixed(self):
        text = "line1\r\nline2\rline3\nline4"
        assert normalize_inbound_text_newlines(text) == "line1\nline2\nline3\nline4"


class TestSanitizeSystemTags:
    def test_passthrough(self):
        assert sanitize_inbound_system_tags("hello") == "hello"

    def test_empty(self):
        assert sanitize_inbound_system_tags("") == ""


class TestDeliveryHints:
    def test_constants(self):
        assert "message_tool" in MESSAGE_TOOL_DELIVERY_HINTS
        assert MESSAGE_TOOL_ONLY_DELIVERY_HINT == "message_tool_only"
        assert "legacy_message_tool" in LEGACY_MESSAGE_TOOL_DELIVERY_HINTS
