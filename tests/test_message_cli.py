"""Tests for cli/program/message — helpers and registration."""

from __future__ import annotations

from openclaw.cli.program.message import (
    MessageCliHelpers,
    collect_option,
)


class TestCollectOption:
    def test_first_value(self):
        result = collect_option("a", None)
        assert result == ["a"]

    def test_append(self):
        result = collect_option("b", ["a"])
        assert result == ["a", "b"]

    def test_none_value(self):
        result = collect_option(None, ["a"])
        assert result == ["a"]

    def test_empty_previous(self):
        result = collect_option("x", [])
        assert result == ["x"]


class TestMessageCliHelpers:
    async def test_run_action_not_implemented(self):
        helpers = MessageCliHelpers()
        result = await helpers.run_message_action("test", {})
        assert result["ok"] is False
        assert "not implemented" in result["error"]

    async def test_run_action_with_callback(self):
        async def callback(action: str, options: dict):
            return {"ok": True, "action": action, "options": options}

        helpers = MessageCliHelpers(run_action=callback)
        result = await helpers.run_message_action("broadcast", {"targets": ["tg:1"]})
        assert result["ok"] is True
        assert result["action"] == "broadcast"

    async def test_run_action_sync_callback(self):
        def callback(action: str, options: dict):
            return {"ok": True, "action": action}

        helpers = MessageCliHelpers(run_action=callback)
        result = await helpers.run_message_action("poll", {"question": "test"})
        assert result["ok"] is True
        assert result["action"] == "poll"
