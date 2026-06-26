"""Tests for secrets resolve types."""

from openclaw.secrets.resolve_types import SecretRefResolveCache


def test_empty_cache():
    cache: SecretRefResolveCache = {}
    assert cache == {}


def test_with_resolved_map():
    cache: SecretRefResolveCache = {
        "resolvedByRefKey": {"key1": "value1"},
    }
    assert cache["resolvedByRefKey"]["key1"] == "value1"


def test_with_file_payload_map():
    cache: SecretRefResolveCache = {
        "filePayloadByProvider": {"provider1": "payload"},
    }
    assert cache["filePayloadByProvider"]["provider1"] == "payload"


def test_both_maps():
    cache: SecretRefResolveCache = {
        "resolvedByRefKey": {"k": "v"},
        "filePayloadByProvider": {"p": "d"},
    }
    assert len(cache) == 2
