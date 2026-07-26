"""Tests for Discord thread binding API."""

from __future__ import annotations

from openclaw_extensions.discord.thread_binding_api import default_top_level_placement


def test_default_top_level_placement() -> None:
    assert default_top_level_placement == "child"
