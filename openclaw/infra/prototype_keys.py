"""Keys blocked from object writes to avoid prototype pollution at untrusted boundaries.

Mirrors src/infra/prototype-keys.ts.
"""

from __future__ import annotations

_BLOCKED_OBJECT_KEYS = frozenset({"__proto__", "prototype", "constructor"})


def is_blocked_object_key(key: str) -> bool:
    """Return True when assigning ``key`` could mutate an object prototype."""
    return key in _BLOCKED_OBJECT_KEYS
