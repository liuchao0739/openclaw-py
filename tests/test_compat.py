"""Tests for compat — legacy names."""

from openclaw.compat import (
    LEGACY_MANIFEST_KEYS,
    LEGACY_PROJECT_NAMES,
    MACOS_APP_SOURCES_DIR,
    MANIFEST_KEY,
    PROJECT_NAME,
)


class TestLegacyNames:
    def test_project_name(self):
        assert PROJECT_NAME == "openclaw"

    def test_manifest_key(self):
        assert MANIFEST_KEY == "openclaw"

    def test_legacy_names(self):
        assert "clawdbot" in LEGACY_PROJECT_NAMES
        assert LEGACY_MANIFEST_KEYS == LEGACY_PROJECT_NAMES

    def test_macos_dir(self):
        assert "OpenClaw" in MACOS_APP_SOURCES_DIR
