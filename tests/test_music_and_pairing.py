"""Tests for music-generation and pairing modules."""

from openclaw.music_generation.model_ref import parse_music_generation_model_ref
from openclaw.pairing.pairing_messages import build_pairing_reply
from openclaw.pairing.pairing_labels import resolve_pairing_id_label, get_pairing_adapter
from openclaw.pairing.pairing_store_types import PairingChannel


class TestParseMusicGenerationModelRef:
    def test_valid(self):
        assert parse_music_generation_model_ref("suno/v4") == {"provider": "suno", "model": "v4"}

    def test_none(self):
        assert parse_music_generation_model_ref(None) is None

    def test_empty(self):
        assert parse_music_generation_model_ref("") is None

    def test_no_slash(self):
        assert parse_music_generation_model_ref("suno") is None


class TestBuildPairingReply:
    def test_basic(self):
        result = build_pairing_reply({
            "channel": "telegram",
            "idLine": "Your Telegram id: 12345",
            "code": "ABC123",
        })
        assert "OpenClaw: access not configured." in result
        assert "Your Telegram id: 12345" in result
        assert "ABC123" in result
        assert "openclaw pairing approve telegram ABC123" in result

    def test_has_code_blocks(self):
        result = build_pairing_reply({
            "channel": "discord",
            "idLine": "id: 67890",
            "code": "XYZ",
        })
        assert "```" in result


class TestResolvePairingIdLabel:
    def test_telegram(self):
        assert resolve_pairing_id_label("telegram") == "Telegram user id"

    def test_discord(self):
        assert resolve_pairing_id_label("discord") == "Discord user id"

    def test_unknown_channel(self):
        assert resolve_pairing_id_label("unknown") == "userId"

    def test_get_adapter(self):
        adapter = get_pairing_adapter("slack")
        assert adapter is not None
        assert adapter["idLabel"] == "Slack user id"

    def test_get_adapter_unknown(self):
        assert get_pairing_adapter("unknown") is None


class TestPairingChannel:
    def test_type_alias(self):
        channel: PairingChannel = "telegram"
        assert channel == "telegram"
