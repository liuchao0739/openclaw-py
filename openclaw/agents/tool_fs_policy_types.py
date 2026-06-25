"""Filesystem policy for agent tools that can touch local paths."""

from __future__ import annotations

from typing import TypedDict


class ToolFsPolicy(TypedDict):
    workspaceOnly: bool
