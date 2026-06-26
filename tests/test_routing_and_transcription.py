"""Tests for routing and realtime-transcription modules."""

from openclaw.routing.peer_kind_match import peer_kind_matches
from openclaw.routing.default_account_warnings import (
    format_channel_accounts_default_path,
    format_set_explicit_default_instruction,
    format_set_explicit_default_to_configured_instruction,
)
from openclaw.realtime_transcription.provider_types import (
    RealtimeTranscriptionSessionCallbacks,
    RealtimeTranscriptionSession,
)


class TestPeerKindMatch:
    def test_same_kind(self):
        assert peer_kind_matches("group", "group") is True
        assert peer_kind_matches("channel", "channel") is True
        assert peer_kind_matches("dm", "dm") is True

    def test_group_channel_compatible(self):
        assert peer_kind_matches("group", "channel") is True
        assert peer_kind_matches("channel", "group") is True

    def test_incompatible(self):
        assert peer_kind_matches("group", "dm") is False
        assert peer_kind_matches("dm", "group") is False
        assert peer_kind_matches("channel", "dm") is False


class TestDefaultAccountWarnings:
    def test_format_accounts_default_path(self):
        assert format_channel_accounts_default_path("telegram") == "channels.telegram.accounts.default"

    def test_format_set_explicit_default(self):
        result = format_set_explicit_default_instruction("discord")
        assert "channels.discord.defaultAccount" in result
        assert "channels.discord.accounts.default" in result

    def test_format_set_explicit_to_configured(self):
        result = format_set_explicit_default_to_configured_instruction({"channelKey": "slack"})
        assert "channels.slack.defaultAccount" in result
        assert "one of these accounts" in result


class TestRealtimeTranscriptionTypes:
    def test_callbacks_typeddict(self):
        callbacks: RealtimeTranscriptionSessionCallbacks = {
            "onPartial": lambda s: None,
            "onTranscript": lambda s: None,
        }
        assert "onPartial" in callbacks

    def test_session_protocol(self):
        class MySession:
            async def connect(self): pass
            def send_audio(self, audio): pass
            def close(self): pass
            def is_connected(self): return True
        session = MySession()
        assert isinstance(session, RealtimeTranscriptionSession)
