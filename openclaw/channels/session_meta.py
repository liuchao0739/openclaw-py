"""Best-effort inbound session metadata recorder for channel plugin command handlers.

Mirrors src/channels/session-meta.ts.
"""

from __future__ import annotations

from typing import Any

async def record_inbound_session_meta_safe(*args: Any, **kwargs: Any) -> Any: ...
