"""Tests for channels/plugins/outbound and status-issues."""

from __future__ import annotations

from openclaw.channels.plugins.outbound import (
    action_capacity,
    build_interactive_presentation,
    fallback_list_block,
    fits_byte_limit,
    format_direct_text_payload,
    is_interactive_presentation,
    split_text_and_media,
    truncate_presentation_text,
    truncate_text,
    truncate_utf8_bytes,
)
from openclaw.channels.plugins.status_issues import (
    deduplicate_issues,
    format_status_issue,
    is_critical_issue,
)


class TestPresentationLimits:
    def test_truncate_text(self):
        assert truncate_text("hello world", 5) == "hello"

    def test_truncate_text_no_limit(self):
        assert truncate_text("hello", None) == "hello"

    def test_truncate_utf8_bytes(self):
        result = truncate_utf8_bytes("hello", 3)
        assert len(result.encode("utf-8")) <= 3

    def test_truncate_presentation_text(self):
        assert truncate_presentation_text("hello world", max_length=5) == "hello"

    def test_fits_byte_limit(self):
        assert fits_byte_limit("hello", 100) is True
        assert fits_byte_limit("hello", 3) is False
        assert fits_byte_limit(None, 100) is True

    def test_action_capacity(self):
        assert action_capacity(max_actions=10, max_rows=2, max_actions_per_row=3) == 6
        assert action_capacity(max_actions=10) == 10
        assert action_capacity() is None

    def test_fallback_list_block(self):
        result = fallback_list_block("context", "Options", ["a", "b", "c"])
        assert result is not None
        assert "Options:" in result["text"]
        assert "- a" in result["text"]

    def test_fallback_list_block_empty(self):
        assert fallback_list_block("text", "Options", []) is None


class TestDirectTextMedia:
    def test_format_text_only(self):
        payload = format_direct_text_payload("hello")
        assert payload["text"] == "hello"
        assert "mediaUrls" not in payload

    def test_format_with_media(self):
        payload = format_direct_text_payload("hello", ["url1", "url2"])
        assert payload["mediaUrls"] == ["url1", "url2"]

    def test_split(self):
        text, urls = split_text_and_media({"text": "hello", "mediaUrls": ["u1"]})
        assert text == "hello"
        assert urls == ["u1"]


class TestInteractive:
    def test_build_basic(self):
        pres = build_interactive_presentation("hello")
        assert pres["type"] == "presentation"
        assert any(b["type"] == "text" for b in pres["blocks"])

    def test_build_with_buttons(self):
        pres = build_interactive_presentation("hello", buttons=[{"label": "OK"}])
        assert any(b["type"] == "actions" for b in pres["blocks"])

    def test_is_interactive(self):
        assert is_interactive_presentation({"type": "presentation"}) is True
        assert is_interactive_presentation({"type": "text"}) is False


class TestStatusIssues:
    def test_format_issue(self):
        issue = format_status_issue("telegram", "auth_failed", "Token expired")
        assert issue["channel"] == "telegram"
        assert issue["type"] == "auth_failed"
        assert issue["severity"] == "warning"

    def test_format_issue_with_account(self):
        issue = format_status_issue("telegram", "auth", "err", account_id="acc1")
        assert issue["accountId"] == "acc1"

    def test_is_critical(self):
        assert is_critical_issue({"severity": "error"}) is True
        assert is_critical_issue({"severity": "warning"}) is False

    def test_deduplicate(self):
        issues = [
            {"channel": "tg", "type": "auth", "accountId": "a1"},
            {"channel": "tg", "type": "auth", "accountId": "a1"},
            {"channel": "tg", "type": "auth", "accountId": "a2"},
        ]
        result = deduplicate_issues(issues)
        assert len(result) == 2
