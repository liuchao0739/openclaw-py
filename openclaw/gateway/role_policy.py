"""Gateway connection role policy.

Mirrors src/gateway/role-policy.ts.
"""

from __future__ import annotations

from typing import Any

GatewayRole = Any

def parse_gateway_role(*args: Any, **kwargs: Any) -> Any: ...
def role_can_skip_device_identity(*args: Any, **kwargs: Any) -> Any: ...
def is_role_authorized_for_method(*args: Any, **kwargs: Any) -> Any: ...
