"""Tests for commands/channel_setup — registry and types."""

from __future__ import annotations

from openclaw.commands.channel_setup import (
    resolve_channel_setup_wizard_adapter_for_plugin,
)


class _ImperativeAdapter:
    """Test imperative adapter with getStatus and configure methods."""

    def getStatus(self):
        return {"connected": True}

    def configure(self, params):
        return {"ok": True, "params": params}


class _Plugin:
    """Test plugin with setupWizard."""

    def __init__(self, setup_wizard=None):
        self.setupWizard = setup_wizard


class TestResolveSetupWizardAdapter:
    def test_none_plugin(self):
        assert resolve_channel_setup_wizard_adapter_for_plugin(None) is None

    def test_plugin_without_setup_wizard(self):
        plugin = _Plugin(None)
        assert resolve_channel_setup_wizard_adapter_for_plugin(plugin) is None

    def test_imperative_adapter(self):
        adapter = _ImperativeAdapter()
        plugin = _Plugin(adapter)
        result = resolve_channel_setup_wizard_adapter_for_plugin(plugin)
        assert result is adapter

    def test_declarative_wizard(self):
        wizard = {
            "status": {"connected": False},
            "credentials": {"token": "required"},
        }
        plugin = _Plugin(wizard)
        result = resolve_channel_setup_wizard_adapter_for_plugin(plugin)
        assert result is not None
        assert result.getStatus() == {"connected": False}

    def test_declarative_wizard_cached(self):
        wizard = {
            "status": {"connected": False},
            "credentials": {"token": "required"},
        }
        plugin = _Plugin(wizard)
        first = resolve_channel_setup_wizard_adapter_for_plugin(plugin)
        second = resolve_channel_setup_wizard_adapter_for_plugin(plugin)
        assert first is second  # Same cached adapter

    def test_non_wizard_object(self):
        plugin = _Plugin({"random": "data"})
        assert resolve_channel_setup_wizard_adapter_for_plugin(plugin) is None

    def test_dict_plugin(self):
        """Test plugin as dict (not object)."""
        adapter = _ImperativeAdapter()
        plugin = {"setupWizard": adapter}
        result = resolve_channel_setup_wizard_adapter_for_plugin(plugin)
        # Dict plugins don't have getattr, so setupWizard lookup uses .get()
        assert result is adapter
