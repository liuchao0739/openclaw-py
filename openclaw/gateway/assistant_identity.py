"""Gateway assistant identity resolver.

Mirrors src/gateway/assistant-identity.ts.
"""

from __future__ import annotations

from typing import Any

DEFAULT_ASSISTANT_IDENTITY: Any = None

def resolve_assistant_identity(*args: Any, **kwargs: Any) -> Any: ...
