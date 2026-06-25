"""Tests for agents/harness — result classification, hook history, compaction recovery."""

from __future__ import annotations

import pytest

from openclaw.agents.harness.compaction_recovery import (
    is_recoverable_native_harness_binding_failure,
    is_recoverable_native_harness_binding_reason,
)
from openclaw.agents.harness.hook_context import build_agent_hook_context
from openclaw.agents.harness.hook_history import (
    MAX_AGENT_HOOK_HISTORY_MESSAGES,
    build_agent_hook_conversation_messages,
    limit_agent_hook_history_messages,
)
from openclaw.agents.harness.result_classification import (
    apply_agent_harness_result_classification,
)


class TestResultClassification:
    def test_no_classifier_adds_harness_id(self):
        class Harness:
            id = "openclaw"

        result = {"aborted": False}
        out = apply_agent_harness_result_classification(Harness(), result, {})
        assert out["agentHarnessId"] == "openclaw"
        assert out["aborted"] is False

    def test_classifier_ok_strips_classification(self):
        class Harness:
            id = "codex"

            def classify(self, result, params):
                return "ok"

        out = apply_agent_harness_result_classification(Harness(), {"aborted": False}, {})
        assert out["agentHarnessId"] == "codex"
        assert "agentHarnessResultClassification" not in out

    def test_classifier_non_ok_sets_classification(self):
        class Harness:
            id = "codex"

            def classify(self, result, params):
                return "error"

        out = apply_agent_harness_result_classification(Harness(), {"aborted": False}, {})
        assert out["agentHarnessId"] == "codex"
        assert out["agentHarnessResultClassification"] == "error"

    def test_replaces_stale_classification(self):
        class Harness:
            id = "codex"

            def classify(self, result, params):
                return "aborted"

        out = apply_agent_harness_result_classification(
            Harness(),
            {"aborted": False, "agentHarnessResultClassification": "error"},
            {},
        )
        assert out["agentHarnessResultClassification"] == "aborted"


class TestHookHistory:
    def test_limit_caps_at_max(self):
        messages = list(range(150))
        limited = limit_agent_hook_history_messages(messages)
        assert len(limited) == MAX_AGENT_HOOK_HISTORY_MESSAGES
        assert limited[0] == 50

    def test_limit_zero_returns_empty(self):
        assert limit_agent_hook_history_messages([1, 2, 3], 0) == []

    def test_limit_custom_max(self):
        assert limit_agent_hook_history_messages([1, 2, 3, 4, 5], 3) == [3, 4, 5]

    def test_build_conversation_messages(self):
        result = build_agent_hook_conversation_messages(
            history_messages=[1, 2, 3],
            current_turn_messages=[4, 5],
        )
        assert result == [1, 2, 3, 4, 5]

    def test_build_with_empty_history(self):
        result = build_agent_hook_conversation_messages(current_turn_messages=[1])
        assert result == [1]


class TestHookContext:
    def test_includes_only_present_fields(self):
        ctx = build_agent_hook_context(
            {"runId": "run-1", "agentId": "agent-1", "sessionKey": None}
        )
        assert ctx["runId"] == "run-1"
        assert ctx["agentId"] == "agent-1"
        assert "sessionKey" not in ctx

    def test_includes_all_fields(self):
        ctx = build_agent_hook_context(
            {
                "runId": "run-1",
                "agentId": "a1",
                "sessionId": "s1",
                "modelId": "gpt-4",
                "contextTokenBudget": 4096,
            }
        )
        assert ctx["runId"] == "run-1"
        assert ctx["agentId"] == "a1"
        assert ctx["sessionId"] == "s1"
        assert ctx["modelId"] == "gpt-4"
        assert ctx["contextTokenBudget"] == 4096


class TestCompactionRecovery:
    @pytest.mark.parametrize(
        "reason,expected",
        [
            ("missing_thread_binding", True),
            ("stale_thread_binding", True),
            ("Thread not found", True),
            ("no thread binding detected", True),
            ("unrelated error", False),
            ("", False),
            (None, False),
            (123, False),
        ],
    )
    def test_is_recoverable_reason(self, reason, expected):
        assert is_recoverable_native_harness_binding_reason(reason) is expected

    def test_binding_failure_with_failure_reason(self):
        result = {"ok": False, "failure": {"reason": "missing_thread_binding"}}
        assert is_recoverable_native_harness_binding_failure(result) is True

    def test_binding_failure_with_top_level_reason(self):
        result = {"ok": False, "reason": "stale_thread_binding"}
        assert is_recoverable_native_harness_binding_failure(result) is True

    def test_binding_failure_ok_result(self):
        assert is_recoverable_native_harness_binding_failure({"ok": True}) is False

    def test_binding_failure_none(self):
        assert is_recoverable_native_harness_binding_failure(None) is False
