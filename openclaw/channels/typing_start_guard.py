"""Circuit breaker for channel typing-start calls.

Mirrors src/channels/typing-start-guard.ts.
"""

from __future__ import annotations

from typing import Any

def create_typing_start_guard(*args: Any, **kwargs: Any) -> Any: ...
