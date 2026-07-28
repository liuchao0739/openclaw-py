from __future__ import annotations

import json
import os
from typing import Any


def list_plugin_files(plugin_dir: str) -> list[str]:
    if not os.path.isdir(plugin_dir):
        return []
    results: list[str] = []
    for root, dirs, files in os.walk(plugin_dir):
        for f in files:
            results.append(os.path.join(root, f))
    return results


def resolve_plugin_relative_path(plugin_dir: str, absolute_path: str) -> str:
    return os.path.relpath(absolute_path, plugin_dir)
