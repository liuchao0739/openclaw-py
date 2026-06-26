"""Tests for media-generation module."""

from openclaw.media_generation import parse_generation_model_ref


def test_valid_ref():
    assert parse_generation_model_ref("openai/dall-e-3") == {"provider": "openai", "model": "dall-e-3"}

def test_none():
    assert parse_generation_model_ref(None) is None

def test_empty():
    assert parse_generation_model_ref("") is None

def test_no_slash():
    assert parse_generation_model_ref("dall-e-3") is None

def test_with_spaces():
    assert parse_generation_model_ref("  openai/dall-e-3  ") == {"provider": "openai", "model": "dall-e-3"}
