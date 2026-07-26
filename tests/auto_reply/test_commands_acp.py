"""Tests for auto_reply/reply/commands_acp — context, diagnostics, lifecycle, options, shared, targets."""

from __future__ import annotations

import pytest

from openclaw.auto_reply.reply.commands_acp.context import (
    resolve_acp_command_account_id,
    resolve_acp_command_binding_context,
    resolve_acp_command_channel,
    resolve_acp_command_conversation_id,
)
from openclaw.auto_reply.reply.commands_acp.diagnostics import (
    format_acp_runtime_error_text,
    format_acp_session_diagnostics,
    to_acp_runtime_error,
)
from openclaw.auto_reply.reply.commands_acp.lifecycle import (
    format_lifecycle_status,
    get_acp_lifecycle_phase,
    is_acp_session_active,
)
from openclaw.auto_reply.reply.commands_acp.runtime_options import (
    normalize_acp_runtime_options,
    resolve_acp_runtime_options,
)
from openclaw.auto_reply.reply.commands_acp.shared import (
    is_acp_command,
    merge_acp_command_defaults,
    normalize_acp_command,
)
from openclaw.auto_reply.reply.commands_acp.targets import (
    format_acp_target_display,
    is_valid_acp_target,
    resolve_acp_target,
)


class TestContext:
    def test_resolve_channel(self):
        params = {"command": {"channel": "Telegram"}, "ctx": {}}
        assert resolve_acp_command_channel(params) == "telegram"

    def test_resolve_channel_from_ctx(self):
        params = {"command": {}, "ctx": {"channel": "discord"}}
        assert resolve_acp_command_channel(params) == "discord"

    def test_resolve_account_id(self):
        params = {"command": {}, "ctx": {"accountId": "acc-123"}}
        assert resolve_acp_command_account_id(params) == "acc-123"

    def test_resolve_conversation_id(self):
        params = {"command": {"conversationId": "conv-1"}, "ctx": {}}
        assert resolve_acp_command_conversation_id(params) == "conv-1"

    def test_resolve_binding_context(self):
        params = {
            "command": {"channel": "telegram", "conversationId": "c1"},
            "ctx": {"accountId": "a1", "threadId": "t1"},
        }
        ctx = resolve_acp_command_binding_context(params)
        assert ctx["channel"] == "telegram"
        assert ctx["accountId"] == "a1"
        assert ctx["threadId"] == "t1"
        assert ctx["conversationId"] == "c1"


class TestDiagnostics:
    def test_format_error_string(self):
        assert format_acp_runtime_error_text("simple error") == "simple error"

    def test_format_error_dict(self):
        error = {"message": "failed", "code": "TIMEOUT"}
        assert "TIMEOUT" in format_acp_runtime_error_text(error)
        assert "failed" in format_acp_runtime_error_text(error)

    def test_format_error_exception(self):
        assert "test" in format_acp_runtime_error_text(ValueError("test"))

    def test_format_session_diagnostics_empty(self):
        assert "No ACP sessions" in format_acp_session_diagnostics([])

    def test_format_session_diagnostics(self):
        entries = [{"sessionId": "s1", "status": "running", "agentId": "main"}]
        result = format_acp_session_diagnostics(entries)
        assert "s1" in result
        assert "running" in result

    def test_to_acp_runtime_error(self):
        err = to_acp_runtime_error(ValueError("test"))
        assert err["message"] == "test"
        assert err["code"] == "ValueError"


class TestLifecycle:
    def test_get_phase_none(self):
        assert get_acp_lifecycle_phase(None) == "stopped"

    def test_get_phase_running(self):
        assert get_acp_lifecycle_phase({"lifecyclePhase": "running"}) == "running"

    def test_is_active(self):
        assert is_acp_session_active({"lifecyclePhase": "running"}) is True
        assert is_acp_session_active({"lifecyclePhase": "stopped"}) is False
        assert is_acp_session_active(None) is False

    def test_format_status(self):
        status = format_lifecycle_status({"sessionId": "s1", "lifecyclePhase": "running"})
        assert "s1" in status
        assert "running" in status


class TestRuntimeOptions:
    def test_resolve_defaults(self):
        params = {"command": {}, "cfg": {}}
        opts = resolve_acp_runtime_options(params)
        assert opts["timeoutMs"] == 120_000
        assert opts["maxTurns"] == 25

    def test_resolve_from_command(self):
        params = {"command": {"timeoutMs": 5000, "maxTurns": 10}, "cfg": {}}
        opts = resolve_acp_runtime_options(params)
        assert opts["timeoutMs"] == 5000
        assert opts["maxTurns"] == 10

    def test_normalize_invalid(self):
        opts = normalize_acp_runtime_options({"timeoutMs": -1, "maxTurns": 0})
        assert opts["timeoutMs"] == 120_000
        assert opts["maxTurns"] == 25


class TestShared:
    def test_is_acp_command(self):
        assert is_acp_command({"type": "acp"}) is True
        assert is_acp_command({"protocol": "acp"}) is True
        assert is_acp_command({"type": "other"}) is False

    def test_normalize_command(self):
        result = normalize_acp_command({"channel": "telegram", "prompt": "hello"})
        assert result["type"] == "acp"
        assert result["channel"] == "telegram"
        assert result["prompt"] == "hello"

    def test_merge_defaults(self):
        result = merge_acp_command_defaults({"channel": "tg"}, {"timeoutMs": 5000})
        assert result["channel"] == "tg"
        assert result["timeoutMs"] == 5000
        assert result["type"] == "acp"


class TestTargets:
    def test_resolve_target(self):
        params = {"command": {"channel": "telegram"}, "ctx": {"agentId": "main", "sessionId": "s1"}}
        target = resolve_acp_target(params)
        assert target["channel"] == "telegram"
        assert target["agentId"] == "main"
        assert target["sessionId"] == "s1"

    def test_is_valid_target(self):
        assert is_valid_acp_target({"channel": "telegram"}) is True
        assert is_valid_acp_target({}) is False

    def test_format_display(self):
        target = {"channel": "telegram", "agentId": "main", "sessionId": "s1"}
        display = format_acp_target_display(target)
        assert "telegram" in display
        assert "main" in display
        assert "s1" in display

    def test_format_display_empty(self):
        assert format_acp_target_display({}) == "default"
