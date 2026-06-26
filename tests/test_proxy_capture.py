"""Tests for proxy-capture paths module."""

from openclaw.proxy_capture.paths import (
    resolve_debug_proxy_db_path,
    resolve_debug_proxy_blob_dir,
    resolve_debug_proxy_cert_dir,
)


def test_db_path():
    result = resolve_debug_proxy_db_path({"OPENCLAW_STATE_DIR": "/tmp/state"})
    assert result == "/tmp/state/debug-proxy/capture.sqlite"


def test_blob_dir():
    result = resolve_debug_proxy_blob_dir({"OPENCLAW_STATE_DIR": "/tmp/state"})
    assert result == "/tmp/state/debug-proxy/blobs"


def test_cert_dir():
    result = resolve_debug_proxy_cert_dir({"OPENCLAW_STATE_DIR": "/tmp/state"})
    assert result == "/tmp/state/debug-proxy/certs"


def test_default_env():
    # Should use home directory when no env
    import os
    result = resolve_debug_proxy_cert_dir({})
    assert "debug-proxy" in result
    assert "certs" in result


def test_none_env():
    result = resolve_debug_proxy_db_path(None)
    assert "debug-proxy" in result
    assert "capture.sqlite" in result
