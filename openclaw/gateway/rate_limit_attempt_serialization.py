"""Gateway auth rate-limit serialization.

Mirrors src/gateway/rate-limit-attempt-serialization.ts.
"""

from __future__ import annotations

from typing import Any

async def with_serialized_keyed_attempt(*args: Any, **kwargs: Any) -> Any: ...
async def with_serialized_rate_limit_attempt(*args: Any, **kwargs: Any) -> Any: ...
