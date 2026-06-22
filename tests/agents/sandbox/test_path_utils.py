"""Sandbox path utils (P2-0015 partial)."""

from openclaw.agents.sandbox.path_utils import (
    is_path_inside_container_root,
    normalize_container_path,
    relative_path_escapes_container_root,
)


def test_normalize_dot():
    assert normalize_container_path(".") == "/"


def test_inside_root():
    assert is_path_inside_container_root("/workspace", "/workspace/src/a.py")


def test_escape_relative():
    assert relative_path_escapes_container_root("../etc/passwd")