"""Tests for Anthropic Vertex provider discovery entry."""

from __future__ import annotations

from openclaw_extensions.anthropic_vertex.provider_discovery import default


def test_imports_without_loading_full_plugin_entry() -> None:
    assert default["id"] == "anthropic-vertex"
    assert default["catalog"]["order"] == "simple"
