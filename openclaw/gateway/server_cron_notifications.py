"""Gateway cron notification delivery.

Mirrors src/gateway/server-cron-notifications.ts.
"""

from __future__ import annotations

from typing import Any

def dispatch_gateway_cron_finished_notifications(*args: Any, **kwargs: Any) -> Any: ...
async def send_gateway_cron_failure_alert(*args: Any, **kwargs: Any) -> Any: ...
