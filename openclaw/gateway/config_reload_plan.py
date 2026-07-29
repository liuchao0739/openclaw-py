"""Gateway config reload planner.

Mirrors src/gateway/config-reload-plan.ts.
"""

from __future__ import annotations

from typing import Any

ChannelKind = Any
GatewayReloadPlan = Any

def resolve_config_reload_metadata(*args: Any, **kwargs: Any) -> Any: ...
def list_plugin_install_timestamp_metadata_paths(*args: Any, **kwargs: Any) -> Any: ...
def list_plugin_install_whole_record_paths(*args: Any, **kwargs: Any) -> Any: ...
def build_gateway_reload_plan(*args: Any, **kwargs: Any) -> Any: ...
