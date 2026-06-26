"""Tests for gateway server root modules."""

import asyncio

import pytest

from openclaw.gateway.server.close_reason import (
    truncate_close_reason,
    CLOSE_REASON_MAX_BYTES,
)
from openclaw.gateway.server.hook_client_ip_config import resolve_hook_client_ip_config
from openclaw.gateway.server.tls import load_gateway_tls_runtime
from openclaw.gateway.server.presence_events import broadcast_presence_snapshot


class TestCloseReason:
    def test_empty_returns_default(self):
        assert truncate_close_reason("") == "invalid handshake"

    def test_short_reason_unchanged(self):
        assert truncate_close_reason("hello") == "hello"

    def test_long_reason_truncated(self):
        reason = "x" * 200
        result = truncate_close_reason(reason)
        assert len(result.encode("utf-8")) <= CLOSE_REASON_MAX_BYTES

    def test_custom_max_bytes(self):
        result = truncate_close_reason("hello world", 5)
        assert len(result.encode("utf-8")) <= 5

    def test_unicode_safe(self):
        result = truncate_close_reason("é" * 100, 10)
        # Should not raise, result is valid UTF-8
        result.encode("utf-8")

    def test_max_bytes_constant(self):
        assert CLOSE_REASON_MAX_BYTES == 120


class TestHookClientIpConfig:
    def test_full_config(self):
        cfg = {"gateway": {"trustedProxies": ["10.0.0.1"], "allowRealIpFallback": True}}
        result = resolve_hook_client_ip_config(cfg)
        assert result["trusted_proxies"] == ["10.0.0.1"]
        assert result["allow_real_ip_fallback"] is True

    def test_empty_config(self):
        result = resolve_hook_client_ip_config({})
        assert result["trusted_proxies"] is None
        assert result["allow_real_ip_fallback"] is False

    def test_none_config(self):
        result = resolve_hook_client_ip_config(None)
        assert result["trusted_proxies"] is None
        assert result["allow_real_ip_fallback"] is False

    def test_no_gateway_key(self):
        result = resolve_hook_client_ip_config({"other": "value"})
        assert result["trusted_proxies"] is None

    def test_fallback_false_by_default(self):
        cfg = {"gateway": {"trustedProxies": ["10.0.0.1"]}}
        result = resolve_hook_client_ip_config(cfg)
        assert result["allow_real_ip_fallback"] is False


class TestTls:
    def test_load_with_cert(self):
        result = asyncio.run(load_gateway_tls_runtime({"cert": "cert-data", "key": "key-data"}))
        assert result["cert"] == "cert-data"
        assert result["key"] == "key-data"

    def test_load_empty(self):
        result = asyncio.run(load_gateway_tls_runtime(None))
        assert result["cert"] is None

    def test_load_with_ca(self):
        result = asyncio.run(load_gateway_tls_runtime({"ca": "ca-data"}))
        assert result["ca"] == "ca-data"


class TestPresenceEvents:
    def test_broadcast_returns_version(self):
        version = [0]
        health_version = [0]

        def increment():
            version[0] += 1
            return version[0]

        def get_health():
            return health_version[0]

        calls = []

        def broadcast(event_type, payload, options):
            calls.append((event_type, payload, options))

        result = broadcast_presence_snapshot({
            "broadcast": broadcast,
            "increment_presence_version": increment,
            "get_health_version": get_health,
        })
        assert result == 1
        assert len(calls) == 1
        assert calls[0][0] == "presence"
        assert calls[0][2]["dropIfSlow"] is True
        assert calls[0][2]["stateVersion"]["presence"] == 1

    def test_broadcast_increments_version(self):
        version = [10]

        def increment():
            version[0] += 1
            return version[0]

        result = broadcast_presence_snapshot({
            "broadcast": lambda *a, **kw: None,
            "increment_presence_version": increment,
            "get_health_version": lambda: 5,
        })
        assert result == 11
