"""Gateway post-attach startup sidecars.

Mirrors src/gateway/server-startup-post-attach.ts.
"""

from __future__ import annotations

from typing import Any

testing: Any = None

GatewayPostReadySidecarHandle = Any

def stop_post_ready_sidecars_after_close_started(*args: Any, **kwargs: Any) -> Any: ...
async def start_gateway_sidecars(*args: Any, **kwargs: Any) -> Any: ...
async def start_gateway_post_attach_runtime(*args: Any, **kwargs: Any) -> Any: ...
