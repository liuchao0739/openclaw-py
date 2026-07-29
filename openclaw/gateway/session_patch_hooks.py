"""Session patch hook dispatcher.

Mirrors src/gateway/session-patch-hooks.ts.
"""

from __future__ import annotations

from typing import Any

def trigger_session_patch_hook(*args: Any, **kwargs: Any) -> Any: ...
