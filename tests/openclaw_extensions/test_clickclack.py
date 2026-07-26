"""Tests for the clickclack extension entry and API barrels."""

from __future__ import annotations

import importlib

import pytest

from openclaw_extensions.clickclack import index


def test_index_default_entry_metadata() -> None:
    entry = index.default
    assert entry.kind == "bundled-channel-entry"
    assert entry.id == "clickclack"
    assert entry.name == "ClickClack"
    assert entry.description == "ClickClack channel plugin"
    assert callable(entry.register)
    assert callable(entry.load_channel_plugin)
    assert entry.config_schema is not None
    assert callable(entry.config_schema["safeParse"])


def test_api_import_requires_unported_runtime_modules() -> None:
    with pytest.raises(ModuleNotFoundError, match="accounts_runtime"):
        importlib.import_module("openclaw_extensions.clickclack.api")


def test_channel_plugin_api_import_requires_unported_runtime_modules() -> None:
    with pytest.raises(ModuleNotFoundError, match="channel_runtime"):
        importlib.import_module("openclaw_extensions.clickclack.channel_plugin_api")


def test_runtime_api_import_requires_unported_runtime_modules() -> None:
    with pytest.raises(ModuleNotFoundError, match="accounts_runtime"):
        importlib.import_module("openclaw_extensions.clickclack.runtime_api")


def test_register_requires_unported_channel_runtime() -> None:
    class FakeApi:
        registration_mode = "full"
        runtime = object()

        def register_channel(self, _params: object) -> None:
            raise AssertionError("register_channel should not run before channel runtime is ported")

    with pytest.raises(ModuleNotFoundError, match="channel_runtime"):
        index.default.register(FakeApi())
