"""Tests for infra/tls fingerprint normalization."""

from openclaw.infra.tls.fingerprint import normalize_fingerprint


def test_plain_hex():
    assert normalize_fingerprint("ABCDEF0123456789") == "abcdef0123456789"

def test_with_colons():
    assert normalize_fingerprint("AB:CD:EF:01:23:45") == "abcdef012345"

def test_with_sha256_prefix():
    assert normalize_fingerprint("SHA256:ABCDEF") == "abcdef"
    assert normalize_fingerprint("SHA-256:ABCDEF") == "abcdef"
    assert normalize_fingerprint("sha256 ABCDEF") == "abcdef"

def test_with_spaces():
    assert normalize_fingerprint("  ABC DEF  ") == "abcdef"

def test_empty():
    assert normalize_fingerprint("") == ""
    assert normalize_fingerprint("   ") == ""

def test_non_hex_chars_removed():
    assert normalize_fingerprint("AB-CD-EF-GH") == "abcdef"

def test_mixed_case():
    assert normalize_fingerprint("aBcDeF") == "abcdef"

def test_non_string():
    assert normalize_fingerprint(123) == ""

def test_full_sha256():
    fp = "SHA256:AB:CD:EF:01:23:45:67:89:AB:CD:EF:01:23:45:67:89:AB:CD:EF:01:23:45:67:89:AB:CD:EF:01:23:45:67:89"
    result = normalize_fingerprint(fp)
    assert len(result) == 64
    assert result == result.lower()
    assert ":" not in result
