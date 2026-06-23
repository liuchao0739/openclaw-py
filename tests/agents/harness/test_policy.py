"""Harness runtime policy resolution."""

from openclaw.agents.harness.policy import resolve_agent_harness_policy


def test_openai_defaults_to_codex_when_auto():
    result = resolve_agent_harness_policy(provider="openai", config={})
    assert result["runtime"] == "codex"


def test_auto_without_openai():
    result = resolve_agent_harness_policy(provider="anthropic", config={})
    assert result["runtime"] == "auto"