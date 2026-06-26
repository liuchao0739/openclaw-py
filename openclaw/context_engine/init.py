"""Context-engine initialization registers built-in engines before plugin resolution."""

from .legacy_registration import register_legacy_context_engine

_initialized = False


def ensureContextEnginesInitialized() -> None:
    """Ensure all built-in context engines are registered exactly once.

    The legacy engine is always registered as a safe fallback so that
    ``resolveContextEngine()`` can resolve the default "legacy" slot without
    callers needing to remember manual registration.

    Additional engines are registered by their own plugins via
    ``api.registerContextEngine()`` during plugin load.
    """
    global _initialized
    if _initialized:
        return
    _initialized = True
    register_legacy_context_engine()


def _reset_init_for_tests() -> None:
    global _initialized
    _initialized = False
