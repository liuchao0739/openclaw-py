"""Tests for commands/status-all — channel issues."""

from __future__ import annotations

from openclaw.commands.status_all import group_channel_issues_by_channel


class TestGroupChannelIssues:
    def test_empty(self):
        assert group_channel_issues_by_channel([]) == {}

    def test_single_channel(self):
        issues = [
            {"channel": "telegram", "type": "auth"},
            {"channel": "telegram", "type": "connection"},
        ]
        result = group_channel_issues_by_channel(issues)
        assert "telegram" in result
        assert len(result["telegram"]) == 2

    def test_multiple_channels(self):
        issues = [
            {"channel": "telegram", "type": "auth"},
            {"channel": "discord", "type": "connection"},
            {"channel": "telegram", "type": "config"},
        ]
        result = group_channel_issues_by_channel(issues)
        assert len(result) == 2
        assert len(result["telegram"]) == 2
        assert len(result["discord"]) == 1

    def test_preserves_order(self):
        issues = [
            {"channel": "tg", "id": 1},
            {"channel": "tg", "id": 2},
            {"channel": "tg", "id": 3},
        ]
        result = group_channel_issues_by_channel(issues)
        ids = [issue["id"] for issue in result["tg"]]
        assert ids == [1, 2, 3]

    def test_missing_channel_key(self):
        issues = [{"type": "unknown"}, {"type": "other"}]
        result = group_channel_issues_by_channel(issues)
        assert "" in result
        assert len(result[""]) == 2
