"""Adapts declarative and imperative channel setup wizards to the command-facing interface."""

from __future__ import annotations

import weakref
from typing import Any

# Cache for declarative setup wizard adapters keyed by plugin object
_setup_wizard_adapters: weakref.WeakKeyDictionary = weakref.WeakKeyDictionary()


def _is_channel_setup_wizard_adapter(setup_wizard: Any) -> bool:
    """Check if setupWizard is an imperative adapter with getStatus and configure methods."""
    return bool(
        setup_wizard
        and isinstance(setup_wizard, object)
        and callable(getattr(setup_wizard, "getStatus", None))
        and callable(getattr(setup_wizard, "configure", None))
    )


def _is_declarative_channel_setup_wizard(setup_wizard: Any) -> bool:
    """Check if setupWizard is a declarative wizard with status and credentials fields."""
    if not setup_wizard or not isinstance(setup_wizard, dict):
        return False
    return "status" in setup_wizard and "credentials" in setup_wizard


def _build_adapter_from_declarative_wizard(plugin: Any, wizard: dict[str, Any]) -> dict[str, Any]:
    """Build an adapter from a declarative setup wizard definition."""

    class _DeclarativeAdapter:
        def __init__(self, wizard_def: dict[str, Any]) -> None:
            self._wizard = wizard_def

        def getStatus(self) -> dict[str, Any]:
            return dict(self._wizard.get("status", {}))

        def configure(self, params: dict[str, Any]) -> dict[str, Any]:
            credentials = self._wizard.get("credentials", {})
            return {"ok": True, "credentials": credentials, "params": params}

    return _DeclarativeAdapter(wizard)


def resolve_channel_setup_wizard_adapter_for_plugin(
    plugin: Any | None,
) -> Any | None:
    """Resolve the setup wizard adapter exposed by one channel plugin.

    Caches declarative adapters using a WeakKeyDictionary.
    """
    if not plugin:
        return None

    setup_wizard = getattr(plugin, "setupWizard", None) if not isinstance(plugin, dict) else plugin.get("setupWizard")

    if _is_channel_setup_wizard_adapter(setup_wizard):
        return setup_wizard

    if _is_declarative_channel_setup_wizard(setup_wizard):
        # Check cache
        try:
            cached = _setup_wizard_adapters.get(plugin)
            if cached is not None:
                return cached
        except TypeError:
            pass  # Not weakly referenceable

        adapter = _build_adapter_from_declarative_wizard(plugin, setup_wizard)
        try:
            _setup_wizard_adapters[plugin] = adapter
        except TypeError:
            pass  # Not weakly referenceable
        return adapter

    return None
