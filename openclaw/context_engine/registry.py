"""Context-engine registry: owner-scoped engine registration and resolution.

Mirrors src/context-engine/registry.ts semantics:
- Only one engine per name; re-registration by the same owner is allowed if
  ``allowSameOwnerRefresh`` is set; other re-registration raises.
- Resolution returns (engine, owner) so callers can attribute the engine.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Protocol, runtime_checkable

EngineFactory = Callable[[], Awaitable[Any]]


@runtime_checkable
class ContextEngineLike(Protocol):
    """Minimal protocol any context engine must satisfy."""

    name: str


@dataclass
class _Slot:
    factory: EngineFactory
    owner: str
    allow_same_owner_refresh: bool = False
    cached: Any = field(default=None)


class ContextEngineRegistryError(Exception):
    """Base error for registry conflicts."""


class ContextEngineNotRegisteredError(ContextEngineRegistryError):
    """Raised when resolving an engine name that has no registration."""


_registry: dict[str, _Slot] = {}


def registerContextEngineForOwner(
    name: str,
    factory: EngineFactory,
    owner: str,
    *,
    allowSameOwnerRefresh: bool = False,
) -> None:
    """Register ``factory`` under ``name`` owned by ``owner``.

    Re-registration by the same owner is allowed only when
    ``allowSameOwnerRefresh`` is True. Re-registration by a different owner
    always raises ``ContextEngineRegistryError``.
    """
    existing = _registry.get(name)
    if existing is not None:
        if existing.owner == owner and allowSameOwnerRefresh:
            _registry[name] = _Slot(
                factory=factory,
                owner=owner,
                allow_same_owner_refresh=allowSameOwnerRefresh,
            )
            return
        raise ContextEngineRegistryError(
            f"Context engine '{name}' is already registered by owner '{existing.owner}'"
        )
    _registry[name] = _Slot(
        factory=factory,
        owner=owner,
        allow_same_owner_refresh=allowSameOwnerRefresh,
    )


async def resolveContextEngine(name: str) -> tuple[Any, str]:
    """Resolve the engine registered under ``name``.

    Returns ``(engine, owner)``. The factory is called lazily and cached.
    Raises ``ContextEngineNotRegisteredError`` if ``name`` is unknown.
    """
    slot = _registry.get(name)
    if slot is None:
        raise ContextEngineNotRegisteredError(
            f"No context engine registered for name '{name}'"
        )
    if slot.cached is None:
        slot.cached = await slot.factory()
    return slot.cached, slot.owner


def _reset_registry_for_tests() -> None:
    """Clear all registrations (test helper)."""
    _registry.clear()
