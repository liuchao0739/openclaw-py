"""Tests for commands/models — alias, errors, local-url."""

from __future__ import annotations

import pytest

from openclaw.commands.models import (
    MODEL_AVAILABILITY_UNAVAILABLE_CODE,
    format_error_with_stack,
    is_local_base_url,
    normalize_alias,
    should_fallback_to_auth_heuristics,
)


class TestNormalizeAlias:
    def test_valid(self):
        assert normalize_alias("gpt-4") == "gpt-4"
        assert normalize_alias("claude:sonnet") == "claude:sonnet"
        assert normalize_alias("model.v2") == "model.v2"

    def test_empty(self):
        with pytest.raises(ValueError, match="empty"):
            normalize_alias("")
        with pytest.raises(ValueError, match="empty"):
            normalize_alias("   ")

    def test_invalid_chars(self):
        with pytest.raises(ValueError, match="letters"):
            normalize_alias("model with spaces")
        with pytest.raises(ValueError, match="letters"):
            normalize_alias("model/with/slashes")

    def test_trims(self):
        assert normalize_alias("  gpt-4  ") == "gpt-4"


class TestListErrors:
    def test_format_error_with_stack(self):
        err = ValueError("test error")
        result = format_error_with_stack(err)
        assert "test error" in result

    def test_format_non_error(self):
        assert format_error_with_stack("string error") == "string error"

    def test_should_fallback_true(self):
        err = Exception("test")
        err.code = MODEL_AVAILABILITY_UNAVAILABLE_CODE  # type: ignore[attr-defined]
        assert should_fallback_to_auth_heuristics(err) is True

    def test_should_fallback_false(self):
        err = ValueError("test")
        assert should_fallback_to_auth_heuristics(err) is False
        assert should_fallback_to_auth_heuristics("string") is False


class TestIsLocalBaseUrl:
    def test_localhost(self):
        assert is_local_base_url("http://localhost:8080") is True

    def test_127(self):
        assert is_local_base_url("http://127.0.0.1:8080") is True

    def test_wildcard(self):
        assert is_local_base_url("http://0.0.0.0:8080") is True

    def test_ipv6_loopback(self):
        assert is_local_base_url("http://[::1]:8080") is True

    def test_mdns(self):
        assert is_local_base_url("http://myhost.local:8080") is True

    def test_remote(self):
        assert is_local_base_url("https://api.openai.com") is False

    def test_invalid_url(self):
        assert is_local_base_url("not a url") is False
