"""Tests for media-generation catalog helpers."""

from __future__ import annotations

from openclaw_packages.media_generation_core import (
    list_media_generation_provider_models,
    synthesize_media_generation_catalog_entries,
)


def test_synthesizes_stable_static_rows_from_provider_defaults_and_models() -> None:
    capabilities = {
        "generate": {"enabled": True},
        "edit": {"enabled": True, "maxInputImages": 2},
    }

    rows = synthesize_media_generation_catalog_entries(
        kind="image_generation",
        provider={
            "id": "example",
            "label": "Example",
            "default_model": "default-image",
            "models": ["default-image", "alternate-image", "  ", "alternate-image"],
            "capabilities": capabilities,
        },
        modes=["generate", "edit"],
    )

    assert rows == [
        {
            "kind": "image_generation",
            "provider": "example",
            "model": "default-image",
            "label": "Example",
            "source": "static",
            "default": True,
            "capabilities": capabilities,
            "modes": ["generate", "edit"],
        },
        {
            "kind": "image_generation",
            "provider": "example",
            "model": "alternate-image",
            "label": "Example",
            "source": "static",
            "capabilities": capabilities,
            "modes": ["generate", "edit"],
        },
    ]


def test_lists_unique_provider_models_in_display_order() -> None:
    assert list_media_generation_provider_models(
        {
            "default_model": "video-default",
            "models": ["video-default", "video-pro"],
        },
    ) == ["video-default", "video-pro"]


def test_marks_a_trimmed_default_model_as_the_catalog_default() -> None:
    assert synthesize_media_generation_catalog_entries(
        kind="video_generation",
        provider={
            "id": "example",
            "default_model": " video-default ",
            "models": ["video-default"],
            "capabilities": {},
        },
    ) == [
        {
            "kind": "video_generation",
            "provider": "example",
            "model": "video-default",
            "source": "static",
            "default": True,
            "capabilities": {},
        },
    ]
