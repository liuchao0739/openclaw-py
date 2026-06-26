"""Tests for config root modules."""

from openclaw.config.mutation_conflict import ConfigMutationConflictError
from openclaw.config.talk_defaults import (
    describe_talk_silence_timeout_defaults,
    TALK_SILENCE_TIMEOUT_MS_BY_PLATFORM,
)
from openclaw.config.bot_loop_protection import ChannelBotLoopProtectionConfig


def test_mutation_conflict_default_retryable():
    err = ConfigMutationConflictError("race", current_hash="abc")
    assert err.current_hash == "abc"
    assert err.retryable is True
    assert "race" in str(err)


def test_mutation_conflict_non_retryable():
    err = ConfigMutationConflictError("bad", current_hash=None, retryable=False)
    assert err.current_hash is None
    assert err.retryable is False


def test_mutation_conflict_roundtrip():
    import pickle
    err = ConfigMutationConflictError("m", current_hash="h", retryable=False)
    restored = pickle.loads(pickle.dumps(err))
    assert isinstance(restored, ConfigMutationConflictError)
    assert restored.current_hash == "h"
    assert restored.retryable is False


def test_talk_silence_defaults_string():
    s = describe_talk_silence_timeout_defaults()
    assert "700" in s
    assert "900" in s
    assert "macOS" in s
    assert "iOS" in s
    assert "Android" in s


def test_talk_silence_platforms():
    assert TALK_SILENCE_TIMEOUT_MS_BY_PLATFORM["macos"] == 700
    assert TALK_SILENCE_TIMEOUT_MS_BY_PLATFORM["android"] == 700
    assert TALK_SILENCE_TIMEOUT_MS_BY_PLATFORM["ios"] == 900


def test_bot_loop_protection_config_optional_fields():
    cfg: ChannelBotLoopProtectionConfig = {}
    assert cfg == {}

    cfg2: ChannelBotLoopProtectionConfig = {
        "enabled": True,
        "max_events_per_window": 10,
        "window_seconds": 60,
        "cooldown_seconds": 30,
    }
    assert cfg2["enabled"] is True
    assert cfg2["max_events_per_window"] == 10
