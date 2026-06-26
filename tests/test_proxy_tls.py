"""Tests for infra/net/proxy TLS helpers."""

import asyncio
import pytest

from openclaw.infra.net.proxy.proxy_tls import (
    resolve_managed_proxy_ca_file,
    resolve_managed_proxy_ca_file_for_url,
    load_managed_proxy_tls_options,
    load_managed_proxy_tls_options_sync,
)


class TestResolveManagedProxyCaFile:
    def test_override_takes_precedence(self):
        result = resolve_managed_proxy_ca_file({
            "caFileOverride": "/override/ca.pem",
            "config": {"tls": {"caFile": "/config/ca.pem"}},
        })
        assert result == "/override/ca.pem"

    def test_config_fallback(self):
        result = resolve_managed_proxy_ca_file({
            "config": {"tls": {"caFile": "/config/ca.pem"}},
        })
        assert result == "/config/ca.pem"

    def test_none(self):
        assert resolve_managed_proxy_ca_file({}) is None

    def test_empty_strings(self):
        assert resolve_managed_proxy_ca_file({
            "caFileOverride": "  ",
            "config": {"tls": {"caFile": ""}},
        }) is None

    def test_trims_whitespace(self):
        result = resolve_managed_proxy_ca_file({
            "caFileOverride": "  /path/ca.pem  ",
        })
        assert result == "/path/ca.pem"


class TestResolveManagedProxyCaFileForUrl:
    def test_https_url(self):
        result = resolve_managed_proxy_ca_file_for_url({
            "proxyUrl": "https://proxy.example.com:443",
            "config": {"tls": {"caFile": "/ca.pem"}},
        })
        assert result == "/ca.pem"

    def test_http_url_returns_none(self):
        result = resolve_managed_proxy_ca_file_for_url({
            "proxyUrl": "http://proxy.example.com:8080",
            "config": {"tls": {"caFile": "/ca.pem"}},
        })
        assert result is None

    def test_no_url_returns_none(self):
        result = resolve_managed_proxy_ca_file_for_url({
            "config": {"tls": {"caFile": "/ca.pem"}},
        })
        assert result is None

    def test_invalid_url_returns_none(self):
        result = resolve_managed_proxy_ca_file_for_url({
            "proxyUrl": "not-a-url",
            "config": {"tls": {"caFile": "/ca.pem"}},
        })
        assert result is None


class TestLoadManagedProxyTlsOptions:
    def test_none_file(self):
        assert asyncio.run(load_managed_proxy_tls_options(None)) is None

    def test_valid_file(self, tmp_path):
        ca_file = tmp_path / "ca.pem"
        ca_file.write_text("CERTIFICATE DATA")
        result = asyncio.run(load_managed_proxy_tls_options(str(ca_file)))
        assert result == {"ca": "CERTIFICATE DATA"}

    def test_missing_file_raises(self):
        with pytest.raises(OSError):
            asyncio.run(load_managed_proxy_tls_options("/nonexistent/ca.pem"))


class TestLoadManagedProxyTlsOptionsSync:
    def test_none_file(self):
        assert load_managed_proxy_tls_options_sync(None) is None

    def test_valid_file(self, tmp_path):
        ca_file = tmp_path / "ca.pem"
        ca_file.write_text("CERT DATA")
        result = load_managed_proxy_tls_options_sync(str(ca_file))
        assert result == {"ca": "CERT DATA"}

    def test_missing_file_raises(self):
        with pytest.raises(OSError):
            load_managed_proxy_tls_options_sync("/nonexistent/ca.pem")
