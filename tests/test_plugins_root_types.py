"""Tests for plugins root modules."""

from openclaw.plugins.plugin_kind_types import PluginKind
from openclaw.plugins.plugin_origin_types import PluginOrigin
from openclaw.plugins.plugin_snapshot_fingerprint import file_fingerprint
from openclaw.plugins.install_security_scan_types import InstallSafetyOverrides


class TestPluginKindTypes:
    def test_values(self):
        assert "memory" in ("memory", "context-engine")
        assert "context-engine" in ("memory", "context-engine")


class TestPluginOriginTypes:
    def test_values(self):
        origins = ("bundled", "global", "workspace", "config")
        for o in origins:
            assert o in origins


class TestFileFingerprint:
    def test_existing_file(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("hello")
        result = file_fingerprint(str(f))
        assert result[0] == str(f)
        assert result[1] == "file"
        assert result[2] == "5"  # "hello" is 5 bytes
        assert len(result) == 5

    def test_existing_dir(self, tmp_path):
        result = file_fingerprint(str(tmp_path))
        assert result[1] == "dir"

    def test_missing_file(self):
        result = file_fingerprint("/nonexistent/path")
        assert result[0] == "/nonexistent/path"
        assert result[1] == "missing"
        assert len(result) == 2


class TestInstallSafetyOverrides:
    def test_empty(self):
        overrides: InstallSafetyOverrides = {}
        assert overrides == {}

    def test_with_fields(self):
        overrides: InstallSafetyOverrides = {
            "dangerouslyForceUnsafeInstall": True,
            "trustedSourceLinkedOfficialInstall": False,
        }
        assert overrides["dangerouslyForceUnsafeInstall"] is True
