"""Ignore rules helpers for adding ignore-file patterns to matchers."""

from __future__ import annotations

import os
import re
from typing import Any


_IGNORE_FILE_NAMES = [".gitignore", ".ignore", ".fdignore"]


def to_posix_path(path_value: str) -> str:
    return path_value.replace(os.sep, "/")


def _prefix_ignore_pattern(line: str, prefix: str) -> str | None:
    trimmed = line.strip()
    if not trimmed:
        return None
    if trimmed.startswith("#") and not trimmed.startswith("\\#"):
        return None
    pattern = line
    negated = False
    if pattern.startswith("!"):
        negated = True
        pattern = pattern[1:]
    elif pattern.startswith("\\!"):
        pattern = pattern[2:]
    if pattern.startswith("/"):
        pattern = pattern[1:]
    prefixed = f"{prefix}{pattern}" if prefix else pattern
    return f"!{prefixed}" if negated else prefixed


def add_ignore_rules(ig: Any, dir_path: str, root_dir: str) -> None:
    relative_dir = os.path.relpath(dir_path, root_dir)
    prefix = f"{to_posix_path(relative_dir)}/" if relative_dir else ""
    for filename in _IGNORE_FILE_NAMES:
        ignore_path = os.path.join(dir_path, filename)
        if not os.path.exists(ignore_path):
            continue
        try:
            with open(ignore_path, "r", encoding="utf-8") as f:
                content = f.read()
            patterns = []
            for line in re.split(r"\r?\n", content):
                result = _prefix_ignore_pattern(line, prefix)
                if result:
                    patterns.append(result)
            if patterns:
                ig.add(patterns)
        except (IOError, OSError):
            pass
