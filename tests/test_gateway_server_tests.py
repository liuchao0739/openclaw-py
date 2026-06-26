"""Tests for gateway server test utilities."""

from openclaw.gateway.server.tests.test_utils import (
    create_empty_plugin_registry,
    create_test_registry,
)


def test_empty_registry():
    reg = create_empty_plugin_registry()
    assert reg["gateway_handlers"] == {}
    assert reg["http_routes"] == []


def test_create_test_registry_default():
    reg = create_test_registry()
    assert reg["gateway_handlers"] == {}
    assert reg["http_routes"] == []


def test_create_test_registry_with_overrides():
    reg = create_test_registry({"gateway_handlers": {"ping": lambda: None}})
    assert "ping" in reg["gateway_handlers"]


def test_create_test_registry_ensures_defaults():
    reg = create_test_registry({"custom": "value"})
    assert reg["gateway_handlers"] == {}
    assert reg["http_routes"] == []
    assert reg["custom"] == "value"


def test_create_test_registry_http_routes():
    reg = create_test_registry({"http_routes": [{"path": "/api"}]})
    assert reg["http_routes"] == [{"path": "/api"}]


def test_create_test_registry_deep_copy():
    handlers = {"ping": lambda: None}
    reg = create_test_registry({"gateway_handlers": handlers})
    # Modifying the original should not affect the registry
    handlers["pong"] = lambda: None
    assert "pong" not in reg["gateway_handlers"]
