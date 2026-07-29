"""Gateway control-plane audit helpers.

Mirrors src/gateway/control-plane-audit.ts.
"""

from __future__ import annotations

from typing import Any

ControlPlaneActor = Any

def resolve_control_plane_actor(*args: Any, **kwargs: Any) -> Any: ...
def format_control_plane_actor(*args: Any, **kwargs: Any) -> Any: ...
def summarize_changed_paths(*args: Any, **kwargs: Any) -> Any: ...
