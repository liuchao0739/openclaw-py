"""Tests for agents harness, cli-runner, embedded-agent-helpers."""

from openclaw.agents.harness.errors import MissingAgentHarnessError, is_missing_agent_harness_error
from openclaw.agents.harness.hook_history import (
    MAX_AGENT_HOOK_HISTORY_MESSAGES,
    limit_agent_hook_history_messages,
    build_agent_hook_conversation_messages,
)
from openclaw.agents.cli_runner.log import (
    CLI_BACKEND_LOG_OUTPUT_ENV,
    format_cli_backend_output_digest,
)
from openclaw.agents.embedded_agent_helpers.messaging_dedupe import (
    normalize_text_for_comparison,
    is_messaging_tool_duplicate,
    is_messaging_tool_duplicate_normalized,
)


class TestMissingAgentHarnessError:
    def test_creation(self):
        err = MissingAgentHarnessError("my-harness")
        assert "my-harness" in str(err)
        assert err.harness_id == "my-harness"

    def test_is_check(self):
        err = MissingAgentHarnessError("h1")
        assert is_missing_agent_harness_error(err) is True
        assert is_missing_agent_harness_error(ValueError("x")) is False


class TestHookHistory:
    def test_limit(self):
        msgs = list(range(150))
        result = limit_agent_hook_history_messages(msgs)
        assert len(result) == MAX_AGENT_HOOK_HISTORY_MESSAGES
        assert result[0] == 50

    def test_limit_zero(self):
        assert limit_agent_hook_history_messages([1, 2], 0) == []

    def test_limit_small(self):
        assert limit_agent_hook_history_messages([1, 2, 3], 10) == [1, 2, 3]

    def test_build(self):
        result = build_agent_hook_conversation_messages(
            history_messages=[1, 2],
            current_turn_messages=[3, 4],
        )
        assert result == [1, 2, 3, 4]

    def test_build_none(self):
        result = build_agent_hook_conversation_messages()
        assert result == []


class TestCliBackendLog:
    def test_env_var(self):
        assert CLI_BACKEND_LOG_OUTPUT_ENV == "OPENCLAW_CLI_BACKEND_LOG_OUTPUT"

    def test_digest(self):
        result = format_cli_backend_output_digest("hello world")
        assert "outBytes=" in result
        assert "outHash=" in result

    def test_digest_deterministic(self):
        assert format_cli_backend_output_digest("test") == format_cli_backend_output_digest("test")

    def test_digest_different(self):
        assert format_cli_backend_output_digest("a") != format_cli_backend_output_digest("b")


class TestMessagingDedupe:
    def test_normalize(self):
        assert normalize_text_for_comparison("  Hello  WORLD  ") == "hello world"

    def test_no_duplicate_empty_sent(self):
        assert is_messaging_tool_duplicate("hello", []) is False

    def test_too_short(self):
        assert is_messaging_tool_duplicate("short", ["short"]) is False

    def test_exact_duplicate(self):
        text = "This is a long enough message text"
        assert is_messaging_tool_duplicate(text, [text]) is True

    def test_substring_duplicate(self):
        sent = "This is a long enough message text that was sent before"
        new = "This is a long enough message text"
        assert is_messaging_tool_duplicate(new, [sent]) is True

    def test_no_duplicate(self):
        assert is_messaging_tool_duplicate(
            "This is a completely different message text",
            ["This is a long enough message text"],
        ) is False

    def test_normalized_check(self):
        norm = normalize_text_for_comparison("This is a long enough message")
        assert is_messaging_tool_duplicate_normalized(norm, [norm]) is True

    def test_emoji_stripped(self):
        text1 = "Hello world emoji test message 😀"
        text2 = "Hello world emoji test message"
        norm1 = normalize_text_for_comparison(text1)
        norm2 = normalize_text_for_comparison(text2)
        assert norm1 == norm2
