"""Tests for the diagnostics-otel extension entry and API barrel."""

from __future__ import annotations

import pytest

from openclaw.plugin_sdk import diagnostic_runtime, security_runtime
from openclaw_extensions.diagnostics_otel import api, index


def test_api_reexports_plugin_contract() -> None:
    assert api.empty_plugin_config_schema is not None
    assert api.OpenClawPluginApi is not None
    assert api.OpenClawPluginService is not None
    assert api.OpenClawPluginServiceContext is not None
    assert api.create_diagnostic_trace_context is diagnostic_runtime.create_diagnostic_trace_context
    assert api.emit_diagnostic_event is diagnostic_runtime.emit_diagnostic_event
    assert api.on_diagnostic_event is diagnostic_runtime.on_diagnostic_event
    assert api.redact_sensitive_text is security_runtime.redact_sensitive_text


def test_index_default_entry_metadata() -> None:
    entry = index.default
    assert entry.id == "diagnostics-otel"
    assert entry.name == "Diagnostics OpenTelemetry"
    assert "OpenTelemetry" in entry.description
    assert callable(entry.register)
    assert entry.config_schema is not None
    assert callable(entry.config_schema["safeParse"])


def test_register_requires_unported_service_runtime() -> None:
    class FakeApi:
        def register_service(self, _service: object) -> None:
            raise AssertionError("register_service should not run before runtime is ported")

    with pytest.raises(ModuleNotFoundError, match="service_runtime"):
        index.default.register(FakeApi())
