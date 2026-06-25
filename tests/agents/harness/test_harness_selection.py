"""Tests for agents/harness selection, registry, and lifecycle."""

from __future__ import annotations

import asyncio

import pytest

from openclaw.agents.harness.errors import MissingAgentHarnessError
from openclaw.agents.harness.lifecycle import run_agent_harness_lifecycle_attempt
from openclaw.agents.harness.registry import (
    clear_agent_harnesses,
    register_agent_harness,
)
from openclaw.agents.harness.selection import (
    resolve_available_agent_harness_policy,
    run_agent_harness_attempt,
    select_agent_harness,
)


@pytest.fixture(autouse=True)
def _stub_openclaw_harness(monkeypatch):
    """Replace the embedded OpenClaw harness with a test stub."""

    class _StubOpenClawHarness:
        id = "openclaw"
        label = "OpenClaw embedded agent (stub)"

        def supports(self, ctx):
            return {"supported": True, "priority": 0}

        async def run_attempt(self, params):
            return _make_attempt_result("openclaw")

    from openclaw.agents.harness import selection as _selection_mod

    monkeypatch.setattr(_selection_mod, "create_openclaw_agent_harness", _StubOpenClawHarness)


@pytest.fixture(autouse=True)
def _clean_registry():
    clear_agent_harnesses()
    yield
    clear_agent_harnesses()


def _make_attempt_result(session_id: str = "openclaw") -> dict:
    return {
        "aborted": False,
        "externalAbort": False,
        "timedOut": False,
        "idleTimedOut": False,
        "timedOutDuringCompaction": False,
        "promptError": None,
        "promptErrorSource": None,
        "sessionIdUsed": session_id,
        "messagesSnapshot": [],
        "assistantTexts": [f"{session_id} ok"],
    }


class _StubHarness:
    def __init__(self, hid, label, provider_match=None, result=None, classify_result=None):
        self.id = hid
        self.label = label
        self._provider_match = provider_match or set()
        self._result = result or _make_attempt_result(hid)
        self._classify_result = classify_result
        self.run_attempt_calls = []

    def supports(self, ctx):
        if ctx["provider"] in self._provider_match:
            return {"supported": True, "priority": 100}
        return {"supported": False}

    async def run_attempt(self, params):
        self.run_attempt_calls.append(params)
        return self._result

    def classify(self, result, params):
        return self._classify_result


class TestSelectAgentHarness:
    def test_auto_selects_openclaw_when_no_plugins(self):
        harness = select_agent_harness({"provider": "anthropic", "modelId": "sonnet-4"})
        assert harness.id == "openclaw"

    def test_auto_selects_supporting_plugin(self):
        register_agent_harness(
            _StubHarness("codex", "Codex", provider_match={"codex", "openai"})
        )
        harness = select_agent_harness({"provider": "codex", "modelId": "gpt-5"})
        assert harness.id == "codex"

    def test_selects_highest_priority_plugin(self):
        low = _StubHarness("codex-low", "Low", provider_match={"codex"})
        low.supports = lambda ctx: {"supported": True, "priority": 10}
        high = _StubHarness("codex-high", "High", provider_match={"codex"})
        high.supports = lambda ctx: {"supported": True, "priority": 100}
        register_agent_harness(low)
        register_agent_harness(high)
        harness = select_agent_harness({"provider": "codex", "modelId": "gpt-5"})
        assert harness.id == "codex-high"

    def test_falls_back_to_openclaw_when_no_plugin_supports(self):
        register_agent_harness(
            _StubHarness("codex", "Codex", provider_match={"codex"})
        )
        harness = select_agent_harness({"provider": "anthropic", "modelId": "sonnet-4"})
        assert harness.id == "openclaw"

    def test_forced_openclaw_runtime(self):
        register_agent_harness(
            _StubHarness("codex", "Codex", provider_match={"codex"})
        )
        harness = select_agent_harness(
            {"provider": "codex", "modelId": "gpt-5", "agentHarnessRuntimeOverride": "openclaw"}
        )
        assert harness.id == "openclaw"

    def test_missing_agent_harness_error_for_unknown_forced(self):
        with pytest.raises(MissingAgentHarnessError):
            select_agent_harness(
                {"provider": "anthropic", "modelId": "sonnet-4", "agentHarnessRuntimeOverride": "nonexistent"}
            )


class TestRunAgentHarnessAttempt:
    async def test_openclaw_fallback_in_auto_mode(self):
        result = await run_agent_harness_attempt(
            {"provider": "codex", "modelId": "gpt-5", "runId": "r1", "sessionId": "s1"}
        )
        assert result["sessionIdUsed"] == "openclaw"

    async def test_plugin_harness_selected_and_runs(self):
        harness = _StubHarness("codex", "Codex", provider_match={"codex"})
        register_agent_harness(harness)
        result = await run_agent_harness_attempt(
            {"provider": "codex", "modelId": "gpt-5", "runId": "r1", "sessionId": "s1"}
        )
        assert result["sessionIdUsed"] == "codex"
        assert len(harness.run_attempt_calls) == 1

    async def test_plugin_failure_surfaces(self):
        class FailingHarness(_StubHarness):
            async def run_attempt(self, params):
                raise RuntimeError("codex startup failed")

        register_agent_harness(FailingHarness("codex", "Codex", provider_match={"codex"}))
        with pytest.raises(RuntimeError, match="codex startup failed"):
            await run_agent_harness_attempt(
                {"provider": "codex", "modelId": "gpt-5", "runId": "r1", "sessionId": "s1"}
            )

    async def test_classify_annotation(self):
        harness = _StubHarness(
            "codex", "Codex", provider_match={"codex"}, classify_result="empty"
        )
        register_agent_harness(harness)
        result = await run_agent_harness_attempt(
            {"provider": "codex", "modelId": "gpt-5", "runId": "r1", "sessionId": "s1"}
        )
        assert result["agentHarnessId"] == "codex"
        assert result["agentHarnessResultClassification"] == "empty"


class TestResolveAvailablePolicy:
    def test_implicit_codex_falls_back_to_openclaw_when_unregistered(self):
        policy = resolve_available_agent_harness_policy(
            {"provider": "openai", "modelId": "gpt-5"}
        )
        assert policy["runtime"] == "openclaw"
