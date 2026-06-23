"""errors.ts and turns.ts parity tests."""

from openclaw.agents.embedded_agent_helpers.errors import (
    extract_observed_overflow_token_count,
    is_compaction_failure_error,
    is_context_overflow_error,
    is_likely_context_overflow_error,
    is_reasoning_constraint_error_message,
)
from openclaw.agents.embedded_agent_helpers.turns import (
    validate_anthropic_turns,
    validate_gemini_turns,
)


def test_context_overflow_not_tpm():
    assert not is_context_overflow_error("413 TPM limit exceeded tokens per minute")


def test_context_overflow_prompt_too_long():
    assert is_context_overflow_error("prompt is too long for this model")


def test_likely_overflow_excludes_billing():
    assert not is_likely_context_overflow_error("billing quota exceeded request size exceeds")


def test_compaction_failure():
    assert is_compaction_failure_error("auto-compaction failed: context length exceeded")


def test_extract_token_count():
    n = extract_observed_overflow_token_count("requested 12,345 tokens for completion")
    assert n == 12345


def test_gemini_merges_assistant():
    msgs = [
        {"role": "user", "content": "a"},
        {"role": "assistant", "content": [{"type": "text", "text": "1"}]},
        {"role": "assistant", "content": [{"type": "text", "text": "2"}]},
    ]
    out = validate_gemini_turns(msgs)
    assistants = [m for m in out if m.get("role") == "assistant"]
    assert len(assistants) == 1
    assert len(assistants[0]["content"]) == 2


def test_anthropic_strips_dangling_tool_use():
    msgs = [
        {"role": "user", "content": "hi"},
        {
            "role": "assistant",
            "content": [{"type": "toolUse", "id": "x1", "name": "exec"}],
        },
    ]
    out = validate_anthropic_turns(msgs)
    asst = next(m for m in out if m.get("role") == "assistant")
    assert asst["content"] == [{"type": "text", "text": "[tool calls omitted]"}]


def test_reasoning_constraint():
    assert is_reasoning_constraint_error_message("reasoning is mandatory for this model")