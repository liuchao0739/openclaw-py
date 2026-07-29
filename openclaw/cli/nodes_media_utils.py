from __future__ import annotations

from typing import Any


def normalize_media_path(path: str) -> str:
    return path.strip()


def is_valid_media_file(path: str) -> bool:
    import os

    return os.path.isfile(path)
