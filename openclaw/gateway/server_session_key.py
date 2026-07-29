"""Gateway run-id to session-key resolver.

Mirrors src/gateway/server-session-key.ts.
"""

from __future__ import annotations

from typing import Any

def resolve_session_key_for_run(*args: Any, **kwargs: Any) -> Any: ...
def reset_resolved_session_key_for_run_cache_for_test(*args: Any, **kwargs: Any) -> Any: ...
