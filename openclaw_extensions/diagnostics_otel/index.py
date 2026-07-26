"""Diagnostics Otel plugin entrypoint registers its OpenClaw integration."""

from __future__ import annotations

from openclaw.plugin_sdk.plugin_entry import OpenClawPluginApi, define_plugin_entry
from openclaw_extensions.diagnostics_otel.src.service import create_diagnostics_otel_service


def _register(api: OpenClawPluginApi) -> None:
    api.register_service(create_diagnostics_otel_service())


default = define_plugin_entry(
    id="diagnostics-otel",
    name="Diagnostics OpenTelemetry",
    description="Export diagnostics events to OpenTelemetry",
    register=_register,
)
