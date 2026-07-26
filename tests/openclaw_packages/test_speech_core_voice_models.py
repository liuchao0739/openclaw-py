"""Tests for speech-core voice model helpers."""

from __future__ import annotations

from openclaw_packages.speech_core import (
    find_voice_model_provider,
    get_voice_provider_config,
    provider_matches_id,
    resolve_primary_voice_provider_candidate,
    resolve_supported_voice_model_refs,
    resolve_voice_model_refs,
    resolve_voice_provider_candidates,
    synthesize_voice_model_catalog_entries,
    voice_provider_supports_model,
)

OPENAI_PROVIDER = {
    "id": "openai",
    "aliases": ["OpenAI"],
    "label": "OpenAI",
    "default_model": "gpt-4o-mini-tts",
    "models": ["gpt-4o-mini-tts", "gpt-realtime-2"],
}
ELEVENLABS_PROVIDER = {
    "id": "elevenlabs",
    "default_model": "eleven_multilingual_v2",
    "models": ["eleven_multilingual_v2"],
}


def test_provider_matches_id_by_canonical_id_and_alias() -> None:
    assert provider_matches_id(OPENAI_PROVIDER, "openai") is True
    assert provider_matches_id(OPENAI_PROVIDER, "OpenAI") is True
    assert provider_matches_id(OPENAI_PROVIDER, "elevenlabs") is False


def test_find_voice_model_provider_resolves_aliases() -> None:
    assert (
        find_voice_model_provider(providers=[OPENAI_PROVIDER], provider_id="OpenAI")
        == OPENAI_PROVIDER
    )
    assert find_voice_model_provider(providers=[OPENAI_PROVIDER], provider_id="missing") is None


def test_voice_provider_supports_model_checks_default_and_models() -> None:
    assert voice_provider_supports_model(OPENAI_PROVIDER, "gpt-4o-mini-tts") is True
    assert voice_provider_supports_model(OPENAI_PROVIDER, "gpt-realtime-2") is True
    assert voice_provider_supports_model(OPENAI_PROVIDER, "unknown-model") is False
    assert voice_provider_supports_model(None, "gpt-4o-mini-tts") is False


def test_resolve_voice_model_refs_from_string_and_object_config() -> None:
    assert resolve_voice_model_refs("openai/gpt-4o-mini-tts") == [
        {"provider": "openai", "model": "gpt-4o-mini-tts"},
    ]
    assert resolve_voice_model_refs(
        {
            "primary": "openai/gpt-4o-mini-tts",
            "fallbacks": ["elevenlabs/eleven_multilingual_v2", "invalid"],
            "timeoutMs": 12_345.9,
        },
    ) == [
        {"provider": "openai", "model": "gpt-4o-mini-tts", "timeout_ms": 12_345},
        {"provider": "elevenlabs", "model": "eleven_multilingual_v2", "timeout_ms": 12_345},
    ]
    assert resolve_voice_model_refs(None) == []
    assert resolve_voice_model_refs(["not", "a", "config"]) == []


def test_resolve_supported_voice_model_refs_filters_and_canonicalizes_providers() -> None:
    providers = [OPENAI_PROVIDER, ELEVENLABS_PROVIDER]
    assert resolve_supported_voice_model_refs(
        config={
            "primary": "OpenAI/gpt-4o-mini-tts",
            "fallbacks": ["elevenlabs/eleven_multilingual_v2", "openai/unknown-model"],
        },
        providers=providers,
    ) == [
        {"provider": "openai", "model": "gpt-4o-mini-tts"},
        {"provider": "elevenlabs", "model": "eleven_multilingual_v2"},
    ]
    assert resolve_supported_voice_model_refs(
        config={"primary": "openai/gpt-4o-mini-tts"},
        providers=providers,
        provider_id="openai",
    ) == [{"provider": "openai", "model": "gpt-4o-mini-tts"}]


def test_resolve_voice_provider_candidates_orders_primary_fallbacks_and_remaining_providers() -> (
    None
):
    providers = [OPENAI_PROVIDER, ELEVENLABS_PROVIDER]
    assert resolve_voice_provider_candidates(
        primary_provider="openai",
        providers=providers,
        voice_model_config={
            "primary": "openai/gpt-4o-mini-tts",
            "fallbacks": ["openai/gpt-realtime-2", "elevenlabs/eleven_multilingual_v2"],
        },
    ) == [
        {"provider": "openai", "voice_model": {"provider": "openai", "model": "gpt-4o-mini-tts"}},
        {"provider": "openai", "voice_model": {"provider": "openai", "model": "gpt-realtime-2"}},
        {
            "provider": "elevenlabs",
            "voice_model": {"provider": "elevenlabs", "model": "eleven_multilingual_v2"},
        },
    ]
    assert resolve_voice_provider_candidates(
        primary_provider="openai",
        providers=providers,
        voice_model_config=None,
    ) == [
        {"provider": "openai"},
        {"provider": "elevenlabs"},
    ]


def test_resolve_primary_voice_provider_candidate_prefers_supported_primary_ref() -> None:
    providers = [OPENAI_PROVIDER, ELEVENLABS_PROVIDER]
    assert resolve_primary_voice_provider_candidate(
        primary_provider="OpenAI",
        providers=providers,
        voice_model_config={
            "primary": "openai/gpt-4o-mini-tts",
            "fallbacks": ["elevenlabs/eleven_multilingual_v2"],
        },
    ) == {
        "provider": "openai",
        "voice_model": {"provider": "openai", "model": "gpt-4o-mini-tts"},
    }
    assert resolve_primary_voice_provider_candidate(
        primary_provider="openai",
        providers=providers,
        voice_model_config={"primary": "elevenlabs/eleven_multilingual_v2"},
    ) == {"provider": "openai"}


def test_get_voice_provider_config_matches_exact_and_case_insensitive_keys() -> None:
    provider_configs = {
        "OpenAI": {"apiKey": "exact"},
        "elevenlabs": {"apiKey": "eleven"},
    }
    assert get_voice_provider_config(
        provider_configs=provider_configs,
        provider=OPENAI_PROVIDER,
        configured_provider_id="OpenAI",
    ) == {"apiKey": "exact"}
    assert get_voice_provider_config(
        provider_configs=provider_configs,
        provider=ELEVENLABS_PROVIDER,
    ) == {"apiKey": "eleven"}
    assert (
        get_voice_provider_config(
            provider_configs={},
            provider=OPENAI_PROVIDER,
        )
        == {}
    )


def test_synthesize_voice_model_catalog_entries_dedupes_and_marks_default() -> None:
    capabilities = {"tts": True}
    assert synthesize_voice_model_catalog_entries(
        provider={
            "id": "openai",
            "label": "OpenAI",
            "default_model": "gpt-4o-mini-tts",
            "models": ["gpt-4o-mini-tts", "gpt-realtime-2", "  "],
        },
        capabilities=capabilities,
        modes=["tts"],
    ) == [
        {
            "kind": "voice",
            "provider": "openai",
            "model": "gpt-4o-mini-tts",
            "label": "OpenAI",
            "source": "static",
            "default": True,
            "capabilities": capabilities,
            "modes": ["tts"],
        },
        {
            "kind": "voice",
            "provider": "openai",
            "model": "gpt-realtime-2",
            "label": "OpenAI",
            "source": "static",
            "capabilities": capabilities,
            "modes": ["tts"],
        },
    ]
