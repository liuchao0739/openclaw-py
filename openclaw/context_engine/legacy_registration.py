"""Legacy context-engine registration installs the built-in fallback under core ownership."""

from .legacy import LegacyContextEngine
from .registry import registerContextEngineForOwner


def register_legacy_context_engine() -> None:
    """Register the built-in legacy context engine under the core owner.

    Refresh is allowed so tests/bootstrap can re-register after module-state resets.
    """

    async def _factory() -> LegacyContextEngine:
        return LegacyContextEngine()

    registerContextEngineForOwner("legacy", _factory, "core", allowSameOwnerRefresh=True)
