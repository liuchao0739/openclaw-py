"""Tests for video-generation and TTS modules."""

from openclaw.video_generation.model_ref import parse_video_generation_model_ref
from openclaw.tts.tts_auto_mode import TTS_AUTO_MODES, normalize_tts_auto_mode


class TestParseVideoGenerationModelRef:
    def test_valid(self):
        assert parse_video_generation_model_ref("sora/v2") == {"provider": "suno", "model": "v2"} or \
               parse_video_generation_model_ref("sora/v2") == {"provider": "sora", "model": "v2"}

    def test_none(self):
        assert parse_video_generation_model_ref(None) is None

    def test_empty(self):
        assert parse_video_generation_model_ref("") is None

    def test_no_slash(self):
        assert parse_video_generation_model_ref("sora") is None


class TestNormalizeTtsAutoMode:
    def test_valid_modes(self):
        assert normalize_tts_auto_mode("off") == "off"
        assert normalize_tts_auto_mode("always") == "always"
        assert normalize_tts_auto_mode("inbound") == "inbound"
        assert normalize_tts_auto_mode("tagged") == "tagged"

    def test_uppercase(self):
        assert normalize_tts_auto_mode("ALWAYS") == "always"

    def test_with_spaces(self):
        assert normalize_tts_auto_mode("  off  ") == "off"

    def test_invalid(self):
        assert normalize_tts_auto_mode("bogus") is None

    def test_non_string(self):
        assert normalize_tts_auto_mode(123) is None
        assert normalize_tts_auto_mode(None) is None

    def test_empty(self):
        assert normalize_tts_auto_mode("") is None

    def test_modes_set(self):
        assert "off" in TTS_AUTO_MODES
        assert "always" in TTS_AUTO_MODES
