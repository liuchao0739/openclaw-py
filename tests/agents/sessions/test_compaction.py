"""Session compaction token helpers."""

from openclaw.agents.sessions.compaction import (
    DEFAULT_COMPACTION_SETTINGS,
    calculate_context_tokens,
    estimate_tokens,
    should_compact,
)


def test_calculate_context_tokens():
    assert calculate_context_tokens({"input": 100, "output": 50}) == 150


def test_estimate_user_message():
    assert estimate_tokens({"role": "user", "content": "abcd"}) >= 1


def test_should_compact_when_over_threshold():
    settings = dict(DEFAULT_COMPACTION_SETTINGS)
    assert should_compact(200_000, 200_000, settings) is True
    assert should_compact(10_000, 200_000, settings) is False