"""Tests for channels/plugins root — capabilities, status, gates, media limits, TTS."""

from __future__ import annotations

from openclaw.channels.plugins import (
    CHANNEL_MESSAGE_CAPABILITIES,
    create_account_action_gate,
    ensure_configured_binding_builtins_registered,
    format_channel_status_state,
    get_configured_binding_consumers,
    register_configured_binding_consumer,
    resolve_channel_media_max_bytes,
    resolve_channel_tts_voice_delivery,
)


class TestMessageCapabilities:
    def test_capabilities(self):
        assert "presentation" in CHANNEL_MESSAGE_CAPABILITIES
        assert "delivery-pin" in CHANNEL_MESSAGE_CAPABILITIES


class TestStatusState:
    def test_linked(self):
        assert format_channel_status_state("linked") == "linked"

    def test_not_linked(self):
        assert format_channel_status_state("not-linked") == "not linked"

    def test_unstable(self):
        assert format_channel_status_state("unstable") == "auth stabilizing"

    def test_unknown(self):
        assert format_channel_status_state("custom") == "custom"


class TestAccountActionGate:
    def test_account_overrides_base(self):
        gate = create_account_action_gate(
            base_actions={"read": True, "write": True},
            account_actions={"write": False},
        )
        assert gate("read") is True
        assert gate("write") is False

    def test_base_only(self):
        gate = create_account_action_gate(base_actions={"read": True})
        assert gate("read") is True
        assert gate("write") is True  # default

    def test_default(self):
        gate = create_account_action_gate()
        assert gate("anything") is True
        assert gate("anything", False) is False


class TestMediaLimits:
    def test_channel_limit(self):
        def resolver(cfg, account_id):
            return 10

        result = resolve_channel_media_max_bytes({}, resolver, "acc1")
        assert result == 10 * 1024 * 1024

    def test_agent_default(self):
        def resolver(cfg, account_id):
            return None

        cfg = {"agents": {"defaults": {"mediaMaxMb": 5}}}
        result = resolve_channel_media_max_bytes(cfg, resolver)
        assert result == 5 * 1024 * 1024

    def test_no_limit(self):
        def resolver(cfg, account_id):
            return None

        assert resolve_channel_media_max_bytes({}, resolver) is None


class TestTtsCapabilities:
    def test_none_channel(self):
        assert resolve_channel_tts_voice_delivery(None) is None
        assert resolve_channel_tts_voice_delivery("") is None


class TestConfiguredBindings:
    def test_register_and_get(self):
        # Register a test consumer
        test_consumer = {"id": "test"}
        register_configured_binding_consumer(test_consumer)
        consumers = get_configured_binding_consumers()
        assert test_consumer in consumers

    def test_ensure_builtins(self):
        # Should not crash even if ACP consumer module is unavailable
        ensure_configured_binding_builtins_registered()
