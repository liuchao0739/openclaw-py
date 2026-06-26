"""Tests for infra/net root modules."""

from openclaw.infra.net.form_data import is_form_data_like
from openclaw.infra.net.hostname import normalize_hostname
from openclaw.infra.net.redirect_headers import (
    retain_safe_headers_for_cross_origin_redirect,
    CROSS_ORIGIN_REDIRECT_SAFE_HEADERS,
)


class TestIsFormDataLike:
    def test_none(self):
        assert is_form_data_like(None) is False

    def test_non_object(self):
        assert is_form_data_like(42) is False
        assert is_form_data_like("string") is False

    def test_form_data_instance(self):
        class FormData:
            def entries(self):
                pass
        assert is_form_data_like(FormData()) is True

    def test_no_entries_method(self):
        class NotFormData:
            pass
        assert is_form_data_like(NotFormData()) is False


class TestNormalizeHostname:
    def test_basic(self):
        assert normalize_hostname("Example.COM") == "example.com"

    def test_trailing_dots(self):
        assert normalize_hostname("example.com.") == "example.com"
        assert normalize_hostname("example.com...") == "example.com"

    def test_ipv6_brackets(self):
        assert normalize_hostname("[::1]") == "::1"

    def test_whitespace(self):
        assert normalize_hostname("  example.com  ") == "example.com"

    def test_empty(self):
        assert normalize_hostname("") == ""

    def test_non_string(self):
        assert normalize_hostname(123) == ""


class TestRetainSafeHeaders:
    def test_filters_unsafe(self):
        headers = {
            "Authorization": "Bearer token",
            "Accept": "application/json",
            "Cookie": "session=abc",
            "Content-Type": "text/plain",
        }
        result = retain_safe_headers_for_cross_origin_redirect(headers)
        assert "Authorization" not in result
        assert "Cookie" not in result
        assert result["Accept"] == "application/json"
        assert result["Content-Type"] == "text/plain"

    def test_none_returns_none(self):
        assert retain_safe_headers_for_cross_origin_redirect(None) is None

    def test_empty_dict(self):
        assert retain_safe_headers_for_cross_origin_redirect({}) == {}

    def test_case_insensitive_lookup(self):
        headers = {"ACCEPT": "text/html"}
        result = retain_safe_headers_for_cross_origin_redirect(headers)
        assert "ACCEPT" in result

    def test_all_safe_headers_present(self):
        headers = {h: "value" for h in [
            "Accept", "Accept-Encoding", "Accept-Language", "Cache-Control",
            "Content-Language", "Content-Type", "If-Match", "If-Modified-Since",
            "If-None-Match", "If-Unmodified-Since", "Pragma", "Range", "User-Agent",
        ]}
        result = retain_safe_headers_for_cross_origin_redirect(headers)
        assert len(result) == 13
