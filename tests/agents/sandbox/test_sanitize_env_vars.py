"""Sandbox env sanitization (P2-0015 partial)."""

from openclaw.agents.sandbox.sanitize_env_vars import (
    sanitize_env_vars,
    validate_env_var_value,
)


def test_blocks_api_key():
    result = sanitize_env_vars({"OPENAI_API_KEY": "sk-test", "PATH": "/bin"})
    assert "OPENAI_API_KEY" in result.blocked
    assert result.allowed.get("PATH") == "/bin"


def test_null_bytes_blocked():
    assert validate_env_var_value("a\x00b") == "Contains null bytes"