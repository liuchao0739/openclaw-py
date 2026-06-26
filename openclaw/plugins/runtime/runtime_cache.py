"""Defines a lazily computed enumerable property on a runtime facade.

Mirrors src/plugins/runtime/runtime-cache.ts.
"""

from __future__ import annotations

from typing import Any, Callable


def define_cached_value(target: Any, key: str, create: Callable[[], Any]) -> None:
    """Define a lazily computed cached property on target.

    The value is computed on first access and cached for subsequent accesses.
    """
    cache: list[Any] = [None]
    ready: list[bool] = [False]

    def _getter(self: Any) -> Any:
        if not ready[0]:
            cache[0] = create()
            ready[0] = True
        return cache[0]

    # Use object.__setattr__ to avoid triggering __setattr__ on the target
    setattr(target.__class__ if hasattr(target, "__class__") else target, key, property(_getter))
