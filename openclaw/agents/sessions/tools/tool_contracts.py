"""Shared built-in session tool input/detail contracts."""

from __future__ import annotations

from typing import Any, TypedDict


class BashToolInput(TypedDict, total=False):
    command: str
    timeout: int


class BashToolDetails(TypedDict, total=False):
    truncation: Any
    fullOutputPath: str


class EditToolInput(TypedDict):
    path: str
    edits: list[dict[str, str]]


class EditToolDetails(TypedDict, total=False):
    diff: str
    patch: str
    firstChangedLine: int


class FindToolInput(TypedDict, total=False):
    pattern: str
    path: str
    limit: int


class FindToolDetails(TypedDict, total=False):
    truncation: Any
    resultLimitReached: int


class GrepToolInput(TypedDict, total=False):
    pattern: str
    path: str
    glob: str
    ignoreCase: bool
    literal: bool
    context: int
    limit: int


class GrepToolDetails(TypedDict, total=False):
    truncation: Any
    matchLimitReached: int
    linesTruncated: bool


class LsToolInput(TypedDict, total=False):
    path: str
    limit: int


class LsToolDetails(TypedDict, total=False):
    truncation: Any
    entryLimitReached: int


class ReadToolInput(TypedDict, total=False):
    path: str
    offset: int
    limit: int


class ReadToolDetails(TypedDict, total=False):
    truncation: Any


class WriteToolInput(TypedDict):
    path: str
    content: str
