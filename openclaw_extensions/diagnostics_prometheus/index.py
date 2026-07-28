from __future__ import annotations

from openclaw.plugin_sdk.plugin_entry import OpenClawPluginApi, define_plugin_entry
from openclaw_extensions.diagnostics_prometheus.src.service import (
    create_diagnostics_prometheus_exporter,
)

_exporter = create_diagnostics_prometheus_exporter()


def _register(api: OpenClawPluginApi) -> None:
    api.register_service(_exporter.service)
    api.register_http_route(
        {
            "path": "/api/diagnostics/prometheus",
            "auth": "gateway",
            "match": "exact",
            "gatewayRuntimeScopeSurface": "trusted-operator",
            "handler": _exporter.handler,
        }
    )


default = define_plugin_entry(
    id="diagnostics-prometheus",
    name="Diagnostics Prometheus",
    description="Expose OpenClaw diagnostics metrics in Prometheus text format",
    register=_register,
)