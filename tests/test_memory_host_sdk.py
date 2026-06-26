"""Tests for memory-host-sdk modules."""

from openclaw.memory_host_sdk import (
    has_configured_memory_secret_input,
    resolve_memory_secret_input_string,
    check_qmd_binary_availability,
    resolve_qmd_binary_unavailable_reason,
)


class TestHasConfiguredMemorySecretInput:
    def test_string_secret(self):
        assert has_configured_memory_secret_input({"secret": "abc"}) is True

    def test_empty_string(self):
        assert has_configured_memory_secret_input({"secret": ""}) is False
        assert has_configured_memory_secret_input({"secret": "  "}) is False

    def test_dict_secret_with_value(self):
        assert has_configured_memory_secret_input({"secret": {"value": "x"}}) is True

    def test_dict_secret_with_env(self):
        assert has_configured_memory_secret_input({"secret": {"env": "MY_SECRET"}}) is True

    def test_dict_secret_empty(self):
        assert has_configured_memory_secret_input({"secret": {}}) is False

    def test_no_secret(self):
        assert has_configured_memory_secret_input({}) is False

    def test_non_dict(self):
        assert has_configured_memory_secret_input(None) is False
        assert has_configured_memory_secret_input("string") is False

    def test_secret_input_alias(self):
        assert has_configured_memory_secret_input({"secretInput": "x"}) is True


class TestResolveMemorySecretInputString:
    def test_string(self):
        assert resolve_memory_secret_input_string({"secret": "abc"}) == "abc"

    def test_trims(self):
        assert resolve_memory_secret_input_string({"secret": "  abc  "}) == "abc"

    def test_dict_with_value(self):
        assert resolve_memory_secret_input_string({"secret": {"value": "xyz"}}) == "xyz"

    def test_empty(self):
        assert resolve_memory_secret_input_string({"secret": ""}) is None
        assert resolve_memory_secret_input_string({}) is None


class TestQmdBinaryAvailability:
    def test_check_returns_unavailable(self):
        result = check_qmd_binary_availability()
        assert result["available"] is False

    def test_resolve_reason(self):
        result = resolve_qmd_binary_unavailable_reason({"available": False, "reason": "test"})
        assert result == "test"

    def test_resolve_reason_when_available(self):
        result = resolve_qmd_binary_unavailable_reason({"available": True})
        assert result is None
