"""Gateway server discovery helpers.

Mirrors src/gateway/server-discovery.ts.
"""

from __future__ import annotations

from typing import Any

def format_bonjour_instance_name(*args: Any, **kwargs: Any) -> Any: ...
def resolve_bonjour_cli_path(*args: Any, **kwargs: Any) -> Any: ...
async def resolve_tailnet_dns_hint(*args: Any, **kwargs: Any) -> Any: ...
