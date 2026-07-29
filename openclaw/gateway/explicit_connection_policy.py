"""Explicit connection policy decides when CLI gateway calls can avoid reading

Mirrors src/gateway/explicit-connection-policy.ts.
"""

from __future__ import annotations

from typing import Any

def can_skip_gateway_config_load(*args: Any, **kwargs: Any) -> Any: ...
def is_gateway_config_bypass_command_path(*args: Any, **kwargs: Any) -> Any: ...
