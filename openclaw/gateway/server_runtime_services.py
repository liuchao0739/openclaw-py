"""Gateway post-ready runtime services.

Mirrors src/gateway/server-runtime-services.ts.
"""

from __future__ import annotations

from typing import Any

GatewayMaintenanceHandles = Any

def start_gateway_cron_with_logging(*args: Any, **kwargs: Any) -> Any: ...
def schedule_gateway_post_ready_maintenance(*args: Any, **kwargs: Any) -> Any: ...
def activate_gateway_scheduled_services(*args: Any, **kwargs: Any) -> Any: ...
async def run_gateway_post_ready_maintenance(*args: Any, **kwargs: Any) -> Any: ...
