"""Tests for gateway/server-methods core modules."""

from openclaw.gateway.server_methods.base_hash import resolve_base_hash_param
from openclaw.gateway.server_methods.record_shared import normalize_trimmed_string


class TestBaseHash:
    def test_valid_hash(self):
        assert resolve_base_hash_param({"baseHash": "abc123"}) == "abc123"

    def test_trimmed_hash(self):
        assert resolve_base_hash_param({"baseHash": "  abc  "}) == "abc"

    def test_missing_hash(self):
        assert resolve_base_hash_param({}) is None

    def test_non_string_hash(self):
        assert resolve_base_hash_param({"baseHash": 123}) is None
        assert resolve_base_hash_param({"baseHash": None}) is None

    def test_empty_hash(self):
        assert resolve_base_hash_param({"baseHash": ""}) is None
        assert resolve_base_hash_param({"baseHash": "   "}) is None

    def test_non_dict_params(self):
        assert resolve_base_hash_param(None) is None
        assert resolve_base_hash_param("string") is None
        assert resolve_base_hash_param(42) is None


class TestNormalizeTrimmedString:
    def test_valid_string(self):
        assert normalize_trimmed_string("hello") == "hello"

    def test_trims_whitespace(self):
        assert normalize_trimmed_string("  hello  ") == "hello"

    def test_non_string(self):
        assert normalize_trimmed_string(123) is None
        assert normalize_trimmed_string(None) is None
        assert normalize_trimmed_string(True) is None

    def test_empty_string(self):
        assert normalize_trimmed_string("") is None

    def test_whitespace_only(self):
        assert normalize_trimmed_string("   ") is None

    def test_preserves_internal_spaces(self):
        assert normalize_trimmed_string("  hello world  ") == "hello world"
