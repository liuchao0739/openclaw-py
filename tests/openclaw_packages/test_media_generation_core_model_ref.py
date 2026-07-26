"""Tests for media-generation model refs."""

from __future__ import annotations

from openclaw_packages.media_generation_core import (
    parse_generation_model_ref,
    resolve_capability_model_ref_for_providers,
    resolve_capability_provider_model_only_ref,
)


def test_parses_provider_model_refs_without_splitting_slash_containing_model_ids() -> None:
    assert parse_generation_model_ref("fal/fal-ai/flux/dev") == {
        "provider": "fal",
        "model": "fal-ai/flux/dev",
    }


def test_rejects_incomplete_provider_model_refs() -> None:
    assert parse_generation_model_ref(None) is None
    assert parse_generation_model_ref("openai") is None
    assert parse_generation_model_ref("/gpt-image-2") is None
    assert parse_generation_model_ref("openai/") is None


def test_resolves_model_only_refs_from_provider_metadata() -> None:
    assert resolve_capability_provider_model_only_ref(
        raw="fal-ai/flux/dev",
        providers=[
            {
                "id": "fal",
                "default_model": "fal-ai/flux/dev",
                "models": ["fal-ai/flux/dev/image-to-image"],
            },
        ],
    ) == {"provider": "fal", "model": "fal-ai/flux/dev"}


def test_keeps_explicit_provider_refs_ahead_of_colliding_model_only_refs() -> None:
    assert resolve_capability_model_ref_for_providers(
        raw="google/lyria-3-pro-preview",
        parse_model_ref=parse_generation_model_ref,
        providers=[
            {
                "id": "google",
                "default_model": "lyria-3-clip-preview",
                "models": ["lyria-3-pro-preview"],
            },
            {
                "id": "openrouter",
                "default_model": "google/lyria-3-pro-preview",
            },
        ],
    ) == {"provider": "google", "model": "lyria-3-pro-preview"}


def test_matches_provider_aliases_through_a_caller_supplied_normalizer() -> None:
    assert resolve_capability_model_ref_for_providers(
        raw="openai/gpt-image-2",
        parse_model_ref=parse_generation_model_ref,
        normalize_provider_id=lambda value: value.lower(),
        providers=[
            {
                "id": "openai",
                "aliases": ["openai"],
                "default_model": "gpt-image-2",
            },
        ],
    ) == {"provider": "openai", "model": "gpt-image-2"}
