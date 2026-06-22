"""Tests embedded-agent-helpers."""

from openclaw.agents.embedded_agent_helpers import (
    drop_thinking_blocks,
    is_auth_error_message,
    is_rate_limit_error_message,
    is_reasoning_constraint_error_message,
    pick_fallback_thinking_level,
)


def test_reasoning_constraint():
    assert is_reasoning_constraint_error_message("reasoning is mandatory for this model")


def test_rate_limit():
    assert is_rate_limit_error_message("HTTP 429 too many requests")


def test_auth():
    assert is_auth_error_message("401 unauthorized")


def test_pick_fallback_minimal():
    level = pick_fallback_thinking_level(
        message="reasoning is required for this endpoint",
        attempted=set(),
    )
    assert level == "minimal"


def test_drop_thinking_blocks():
    messages = [
        {"role": "assistant", "content": [{"type": "thinking", "thinking": "x"}, {"type": "text", "text": "hi"}]},
        {"role": "assistant", "content": [{"type": "thinking", "thinking": "y"}]},
    ]
    out = drop_thinking_blocks(messages)
    assert out[0]["content"] == [{"type": "text", "text": "hi"}]
    assert out[1]["content"] == [{"type": "thinking", "thinking": "y"}]