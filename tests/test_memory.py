"""Tests for memory root-memory-files module."""

import asyncio
import os
from pathlib import Path

import pytest

from openclaw.memory.root_memory_files import (
    CANONICAL_ROOT_MEMORY_FILENAME,
    LEGACY_ROOT_MEMORY_FILENAME,
    resolve_canonical_root_memory_path,
    resolve_legacy_root_memory_path,
    resolve_root_memory_repair_dir,
    exact_workspace_entry_exists,
    resolve_canonical_root_memory_file,
    should_skip_root_memory_auxiliary_path,
)


class TestResolvePaths:
    def test_canonical(self, tmp_path):
        assert resolve_canonical_root_memory_path(str(tmp_path)) == str(tmp_path / "MEMORY.md")

    def test_legacy(self, tmp_path):
        assert resolve_legacy_root_memory_path(str(tmp_path)) == str(tmp_path / "memory.md")

    def test_repair_dir(self, tmp_path):
        assert resolve_root_memory_repair_dir(str(tmp_path)) == str(tmp_path / ".openclaw-repair" / "root-memory")


class TestExactWorkspaceEntryExists:
    def test_exists(self, tmp_path):
        (tmp_path / "file.txt").write_text("x")
        assert asyncio.run(exact_workspace_entry_exists(str(tmp_path), "file.txt")) is True

    def test_not_exists(self, tmp_path):
        assert asyncio.run(exact_workspace_entry_exists(str(tmp_path), "nope.txt")) is False

    def test_nonexistent_dir(self):
        assert asyncio.run(exact_workspace_entry_exists("/nonexistent", "x")) is False


class TestResolveCanonicalRootMemoryFile:
    def test_finds_file(self, tmp_path):
        (tmp_path / "MEMORY.md").write_text("memory")
        result = asyncio.run(resolve_canonical_root_memory_file(str(tmp_path)))
        assert result is not None
        assert result.endswith("MEMORY.md")

    def test_no_file(self, tmp_path):
        result = asyncio.run(resolve_canonical_root_memory_file(str(tmp_path)))
        assert result is None

    def test_skips_symlink(self, tmp_path):
        target = tmp_path / "target.md"
        target.write_text("x")
        link = tmp_path / "MEMORY.md"
        try:
            os.symlink(target, link)
        except OSError:
            pytest.skip("symlinks not supported")
        result = asyncio.run(resolve_canonical_root_memory_file(str(tmp_path)))
        assert result is None


class TestShouldSkipRootMemoryAuxiliaryPath:
    def test_canonical_not_skipped(self, tmp_path):
        abs_path = str(tmp_path / "MEMORY.md")
        assert should_skip_root_memory_auxiliary_path({
            "workspaceDir": str(tmp_path),
            "absPath": abs_path,
        }) is False

    def test_legacy_skipped(self, tmp_path):
        abs_path = str(tmp_path / "memory.md")
        assert should_skip_root_memory_auxiliary_path({
            "workspaceDir": str(tmp_path),
            "absPath": abs_path,
        }) is True

    def test_repair_dir_skipped(self, tmp_path):
        abs_path = str(tmp_path / ".openclaw-repair" / "root-memory" / "backup.md")
        assert should_skip_root_memory_auxiliary_path({
            "workspaceDir": str(tmp_path),
            "absPath": abs_path,
        }) is True

    def test_outside_workspace_not_skipped(self, tmp_path):
        assert should_skip_root_memory_auxiliary_path({
            "workspaceDir": str(tmp_path),
            "absPath": "/other/path/memory.md",
        }) is False

    def test_normal_file_not_skipped(self, tmp_path):
        abs_path = str(tmp_path / "notes.md")
        assert should_skip_root_memory_auxiliary_path({
            "workspaceDir": str(tmp_path),
            "absPath": abs_path,
        }) is False
