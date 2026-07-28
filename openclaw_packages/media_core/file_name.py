from __future__ import annotations

import ntpath
import posixpath


def basename_from_any_path(value: str) -> str:
    return ntpath.basename(posixpath.basename(value))


def extname_from_any_path(value: str) -> str:
    return ntpath.splitext(basename_from_any_path(value))[1]


def name_from_any_path(value: str) -> str:
    base = basename_from_any_path(value)
    _, ext = ntpath.splitext(base)
    return ntpath.splitext(base)[0]
