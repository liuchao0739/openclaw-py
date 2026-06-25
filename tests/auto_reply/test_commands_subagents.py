"""Tests for auto_reply/reply/commands_subagents — shared, focus, unfocus, help, list, info, log, agents."""

from __future__ import annotations

import time

import pytest

from openclaw.auto_reply.reply.commands_subagents.action_agents import handle_agents_action
from openclaw.auto_reply.reply.commands_subagents.action_focus import handle_focus_action
from openclaw.auto_reply.reply.commands_subagents.action_help import handle_help_action
from openclaw.auto_reply.reply.commands_subagents.action_info import handle_info_action
from openclaw.auto_reply.reply.commands_subagents.action_list import handle_list_action
from openclaw.auto_reply.reply.commands_subagents.action_log import handle_log_action
from openclaw.auto_reply.reply.commands_subagents.action_unfocus import handle_unfocus_action
from openclaw.auto_reply.reply.commands_subagents.shared import (
    format_run_label,
    is_active_run,
    is_recent_run,
    resolve_subagent_target,
    stop_with_text,
)


def _make_run(**kwargs):
    defaults = {
        "runId": "run-abc123def456",
        "sessionId": "session-1",
        "taskName": "research",
        "status": "running",
        "startedAt": time.time() * 1000,
    }
    defaults.update(kwargs)
    return defaults


class TestShared:
    def test_stop_with_text(self):
        result = stop_with_text("hello")
        assert result["shouldContinue"] is False
        assert result["reply"]["text"] == "hello"

    def test_format_run_label(self):
        entry = _make_run()
        label = format_run_label(entry)
        assert "research" in label
        assert "running" in label

    def test_resolve_target_by_index(self):
        runs = [_make_run(), _make_run(runId="run-xyz")]
        result = resolve_subagent_target(runs, "1")
        assert "entry" in result
        assert result["entry"]["runId"] == "run-abc123def456"

    def test_resolve_target_by_id_prefix(self):
        runs = [_make_run()]
        result = resolve_subagent_target(runs, "run-abc")
        assert "entry" in result

    def test_resolve_target_by_task_name(self):
        runs = [_make_run(taskName="research")]
        result = resolve_subagent_target(runs, "research")
        assert "entry" in result

    def test_resolve_target_missing_token(self):
        result = resolve_subagent_target([], None)
        assert "error" in result

    def test_resolve_target_not_found(self):
        runs = [_make_run()]
        result = resolve_subagent_target(runs, "nonexistent")
        assert "error" in result

    def test_is_active_run(self):
        assert is_active_run(_make_run()) is True
        assert is_active_run(_make_run(endedAt=time.time() * 1000)) is False

    def test_is_recent_run(self):
        assert is_recent_run(_make_run(startedAt=time.time() * 1000)) is True
        assert is_recent_run(_make_run(startedAt=time.time() * 1000 - 31 * 60 * 1000)) is False


class TestActions:
    def test_help(self):
        result = handle_help_action({}, [], [])
        assert "Subagent Commands" in result["reply"]["text"]

    def test_list_empty(self):
        result = handle_list_action({}, [], [])
        assert "No subagent runs" in result["reply"]["text"]

    def test_list_with_runs(self):
        runs = [_make_run(), _make_run(taskName="coding", status="completed", endedAt=time.time() * 1000)]
        result = handle_list_action({}, runs, [])
        text = result["reply"]["text"]
        assert "research" in text
        assert "Active" in text

    def test_focus_no_token(self):
        result = handle_focus_action({}, [], [])
        assert "Usage" in result["reply"]["text"]

    def test_focus_valid(self):
        runs = [_make_run()]
        result = handle_focus_action({}, runs, ["1"])
        assert "Focused" in result["reply"]["text"]

    def test_unfocus(self):
        result = handle_unfocus_action({}, [], [])
        assert "Unfocused" in result["reply"]["text"]

    def test_info_no_token(self):
        result = handle_info_action({}, [], [])
        assert "Usage" in result["reply"]["text"]

    def test_info_valid(self):
        runs = [_make_run()]
        result = handle_info_action({}, runs, ["1"])
        text = result["reply"]["text"]
        assert "run-abc" in text
        assert "research" in text

    def test_log_no_token(self):
        result = handle_log_action({}, [], [])
        assert "Usage" in result["reply"]["text"]

    def test_log_no_output(self):
        runs = [_make_run()]
        result = handle_log_action({}, runs, ["1"])
        assert "No log output" in result["reply"]["text"]

    def test_log_with_output(self):
        runs = [_make_run(logLines=["line 1", "line 2"])]
        result = handle_log_action({}, runs, ["1"])
        text = result["reply"]["text"]
        assert "line 1" in text
        assert "line 2" in text

    def test_agents_empty(self):
        result = handle_agents_action({}, [], [])
        assert "No agent harnesses" in result["reply"]["text"]
