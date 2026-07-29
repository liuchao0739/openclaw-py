"""Direct-DM dispatch compatibility facade.

Mirrors src/channels/direct-dm.ts.
"""

from __future__ import annotations

from typing import Any

async def dispatch_inbound_direct_dm_with_runtime(*args: Any, **kwargs: Any) -> Any: ...
