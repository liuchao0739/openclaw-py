"""Tests for logging modules."""

from openclaw.logging.types import LoggerSettings
from openclaw.logging.state import logging_state, LoggingState
from openclaw.logging.redact_identifier import sha256_hex_prefix, redact_identifier


class TestLoggerSettings:
    def test_typeddict(self):
        settings: LoggerSettings = {"level": "info", "file": "/var/log/app.log"}
        assert settings["level"] == "info"


class TestLoggingState:
    def test_defaults(self):
        state = LoggingState()
        assert state.cached_logger is None
        assert state.console_patched is False
        assert state.invalid_env_log_level_value is None

    def test_reset(self):
        state = LoggingState()
        state.console_patched = True
        state.invalid_env_log_level_value = "bad"
        state.reset()
        assert state.console_patched is False
        assert state.invalid_env_log_level_value is None


class TestSha256HexPrefix:
    def test_default_length(self):
        result = sha256_hex_prefix("hello")
        assert len(result) == 12

    def test_custom_length(self):
        result = sha256_hex_prefix("hello", 8)
        assert len(result) == 8

    def test_deterministic(self):
        assert sha256_hex_prefix("test") == sha256_hex_prefix("test")

    def test_different_inputs(self):
        assert sha256_hex_prefix("a") != sha256_hex_prefix("b")

    def test_min_length_1(self):
        result = sha256_hex_prefix("test", 0)
        assert len(result) == 1

    def test_hex_output(self):
        result = sha256_hex_prefix("test")
        assert all(c in "0123456789abcdef" for c in result)


class TestRedactIdentifier:
    def test_valid_string(self):
        result = redact_identifier("user@example.com")
        assert result.startswith("sha256:")
        assert len(result) > 7

    def test_deterministic(self):
        assert redact_identifier("test") == redact_identifier("test")

    def test_empty_returns_dash(self):
        assert redact_identifier("") == "-"
        assert redact_identifier("   ") == "-"

    def test_none_returns_dash(self):
        assert redact_identifier(None) == "-"

    def test_non_string_returns_dash(self):
        assert redact_identifier(123) == "-"

    def test_custom_length(self):
        result = redact_identifier("test", {"len": 8})
        parts = result.split(":")
        assert len(parts[1]) == 8

    def test_trims_whitespace(self):
        assert redact_identifier("  test  ") == redact_identifier("test")
