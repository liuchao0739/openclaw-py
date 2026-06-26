"""Tests for infra root modules."""

import sqlite3
import tempfile
from pathlib import Path

from openclaw.infra.approval_types import ChannelApprovalKind
from openclaw.infra.archive_path import is_windows_drive_path
from openclaw.infra.sqlite_user_version import read_sqlite_user_version


class TestApprovalTypes:
    def test_kind_values(self):
        assert "exec" in ("exec", "plugin")
        assert "plugin" in ("exec", "plugin")


class TestIsWindowsDrivePath:
    def test_windows_path(self):
        assert is_windows_drive_path("C:\\Users\\test") is True
        assert is_windows_drive_path("D:/data") is True

    def test_posix_path(self):
        assert is_windows_drive_path("/usr/local") is False

    def test_relative_path(self):
        assert is_windows_drive_path("relative/path") is False

    def test_empty(self):
        assert is_windows_drive_path("") is False

    def test_non_string(self):
        assert is_windows_drive_path(123) is False

    def test_lowercase_drive(self):
        assert is_windows_drive_path("c:\\test") is True


class TestReadSqliteUserVersion:
    def test_default_zero(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db = sqlite3.connect(f.name)
            assert read_sqlite_user_version(db) == 0
            db.close()

    def test_after_set(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db = sqlite3.connect(f.name)
            db.execute("PRAGMA user_version = 42")
            assert read_sqlite_user_version(db) == 42
            db.close()
