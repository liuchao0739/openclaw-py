"""P2-0008 embedded-agent-helpers additions."""

from openclaw.agents.embedded_agent_helpers.google import is_google_model_api
from openclaw.agents.embedded_agent_helpers.messaging_dedupe import (
    is_messaging_tool_duplicate,
    normalize_text_for_comparison,
)
from openclaw.agents.embedded_agent_helpers.provider_error_patterns import (
    classify_provider_specific_error,
    matches_provider_context_overflow,
)
from openclaw.shared.google_turn_ordering import sanitize_google_assistant_first_ordering


def test_google_api():
    assert is_google_model_api("google-generative-ai")
    assert not is_google_model_api("openai")


def test_assistant_first_bootstrap():
    msgs = [{"role": "assistant", "content": "hi"}]
    out = sanitize_google_assistant_first_ordering(msgs)
    assert out[0]["role"] == "user"
    assert out[1]["role"] == "assistant"


def test_messaging_duplicate():
    long_text = "hello world this is long enough"
    assert is_messaging_tool_duplicate(long_text, [long_text])


def test_provider_overflow():
    assert matches_provider_context_overflow(
        "input token count exceeds the maximum number of input tokens allowed"
    )


def test_throttling_maps_rate_limit():
    assert classify_provider_specific_error("ThrottlingException: slow down") == "rate_limit"


def test_normalize_strips_spaces():
    assert normalize_text_for_comparison("  A   B  ") == "a b"