"""Tests for image-generation core modules."""

from openclaw.image_generation.model_ref import parse_image_generation_model_ref


class TestParseImageGenerationModelRef:
    def test_valid_ref(self):
        result = parse_image_generation_model_ref("openai/dall-e-3")
        assert result == {"provider": "openai", "model": "dall-e-3"}

    def test_with_spaces(self):
        result = parse_image_generation_model_ref("  openai/dall-e-3  ")
        assert result == {"provider": "openai", "model": "dall-e-3"}

    def test_model_with_slash(self):
        result = parse_image_generation_model_ref("provider/model/sub")
        assert result == {"provider": "provider", "model": "model/sub"}

    def test_none_input(self):
        assert parse_image_generation_model_ref(None) is None

    def test_empty_string(self):
        assert parse_image_generation_model_ref("") is None
        assert parse_image_generation_model_ref("   ") is None

    def test_no_slash(self):
        assert parse_image_generation_model_ref("dall-e-3") is None

    def test_empty_provider(self):
        assert parse_image_generation_model_ref("/model") is None

    def test_empty_model(self):
        assert parse_image_generation_model_ref("provider/") is None

    def test_non_string(self):
        assert parse_image_generation_model_ref(123) is None
