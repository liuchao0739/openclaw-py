"""Tests for configured model ref collection."""

from __future__ import annotations

from openclaw_packages.model_catalog_core import (
    collect_configured_model_ref_values,
    collect_configured_model_refs,
    extract_provider_from_model_ref,
)


def test_collects_agent_hook_message_and_channel_model_refs_with_config_paths() -> None:
    assert collect_configured_model_refs(
        {
            "agents": {
                "defaults": {
                    "model": {
                        "primary": "openai/gpt-5.5",
                        "fallbacks": ["anthropic/claude-sonnet-4-6"],
                    },
                    "compaction": {"memoryFlush": {"model": "openai/gpt-5.5-mini"}},
                },
                "list": [{"id": "custom", "model": "xai/grok-4-fast"}],
            },
            "hooks": {
                "mappings": [{"model": "openai/gpt-5.5-nano"}],
            },
            "messages": {
                "tts": {"summaryModel": "openai/gpt-5.5-mini"},
            },
            "channels": {
                "modelByChannel": {
                    "discord": {
                        "guild": "anthropic/claude-opus-4-8",
                    },
                },
            },
        },
    ) == [
        {"path": "agents.defaults.model.primary", "value": "openai/gpt-5.5"},
        {"path": "agents.defaults.model.fallbacks.0", "value": "anthropic/claude-sonnet-4-6"},
        {"path": "agents.defaults.compaction.memoryFlush.model", "value": "openai/gpt-5.5-mini"},
        {"path": "agents.list.0.model", "value": "xai/grok-4-fast"},
        {"path": "channels.modelByChannel.discord.guild", "value": "anthropic/claude-opus-4-8"},
        {"path": "hooks.mappings.0.model", "value": "openai/gpt-5.5-nano"},
        {"path": "messages.tts.summaryModel", "value": "openai/gpt-5.5-mini"},
    ]


def test_can_exclude_channel_model_overrides_from_configured_refs() -> None:
    assert collect_configured_model_ref_values(
        {
            "agents": {"defaults": {"model": "openai/gpt-5.5"}},
            "channels": {
                "modelByChannel": {"discord": {"guild": "anthropic/claude-sonnet-4-6"}},
            },
        },
        include_channel_model_overrides=False,
    ) == ["openai/gpt-5.5"]


def test_ignores_array_shaped_malformed_records() -> None:
    assert collect_configured_model_refs(
        {
            "agents": {
                "defaults": {
                    "models": ["openai/gpt-5.5"],
                },
            },
        },
    ) == []


def test_extracts_normalized_providers_from_provider_prefixed_refs() -> None:
    assert extract_provider_from_model_ref(" OpenAI/gpt-5.5 ") == "openai"
    assert extract_provider_from_model_ref("gpt-5.5") is None
