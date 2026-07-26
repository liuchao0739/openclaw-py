"""Tests for Anthropic Vertex provider policy API."""

from __future__ import annotations

from openclaw_extensions.anthropic_vertex.provider_policy_api import resolve_thinking_profile


def test_leaves_claude_opus_4_8_thinking_off_by_default_with_max_effort_support() -> None:
    profile = resolve_thinking_profile(
        {"provider": "anthropic-vertex", "modelId": "claude-opus-4-8"}
    )
    assert profile is not None
    assert profile["defaultLevel"] == "off"
    assert "max" in [level["id"] for level in profile["levels"]]


def test_keeps_claude_opus_4_7_thinking_off_by_default() -> None:
    profile = resolve_thinking_profile(
        {"provider": "anthropic-vertex", "modelId": "claude-opus-4-7"}
    )
    assert profile is not None
    assert profile["defaultLevel"] == "off"


def test_exposes_native_max_without_xhigh_for_claude_sonnet_4_6() -> None:
    profile = resolve_thinking_profile(
        {"provider": "anthropic-vertex", "modelId": "claude-sonnet-4-6"}
    )
    assert profile is not None
    level_ids = [level["id"] for level in profile["levels"]]
    assert "max" in level_ids
    assert "xhigh" not in level_ids


def test_inherits_claude_fable_5_provider_agnostic_thinking_contract() -> None:
    profile = resolve_thinking_profile(
        {"provider": "anthropic-vertex", "modelId": "claude-fable-5"}
    )
    assert profile is not None
    assert profile["defaultLevel"] == "high"
    assert profile["preserveWhenCatalogReasoningFalse"] is True
    assert "max" in [level["id"] for level in profile["levels"]]


def test_resolves_deployment_aliases_from_canonical_model_metadata() -> None:
    profile = resolve_thinking_profile(
        {
            "provider": "anthropic-vertex",
            "modelId": "production-claude",
            "params": {"canonicalModelId": "claude-fable-5"},
        }
    )
    assert profile is not None
    assert profile["defaultLevel"] == "high"
    assert profile["preserveWhenCatalogReasoningFalse"] is True


def test_ignores_other_providers() -> None:
    assert resolve_thinking_profile({"provider": "anthropic", "modelId": "claude-opus-4-8"}) is None
