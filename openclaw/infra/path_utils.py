from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def resolve_path_env(path_str: str) -> str:
    if not path_str:
        return path_str
    return os.path.expandvars(os.path.expanduser(path_str))


def resolve_path_guards(path_str: str, root_dir: str | None = None) -> str:
    resolved = resolve_path_env(path_str)
    if root_dir and not os.path.isabs(resolved):
        resolved = os.path.join(root_dir, resolved)
    return os.path.normpath(resolved)


def resolve_path_prepend(paths: list[str] | None = None) -> str:
    if not paths:
        return ""
    return os.pathsep.join(paths)


def resolve_path_safety(
    path_str: str,
    allowed_roots: list[str] | None = None,
) -> bool:
    resolved = resolve_path_env(path_str)
    if not os.path.isabs(resolved):
        return True
    if not allowed_roots:
        return True
    real_resolved = os.path.realpath(resolved)
    for root in allowed_roots:
        real_root = os.path.realpath(root)
        if real_resolved.startswith(real_root):
            return True
    return False


def is_path_inside(path: str, root: str) -> bool:
    try:
        real_path = os.path.realpath(path)
        real_root = os.path.realpath(root)
        return real_path.startswith(real_root + os.sep) or real_path == real_root
    except (OSError, ValueError):
        return False


def normalize_paths_in_config(config: dict[str, Any]) -> dict[str, Any]:
    if isinstance(config, dict):
        result = {}
        for key, value in config.items():
            if isinstance(value, str):
                result[key] = resolve_path_env(value)
            elif isinstance(value, (dict, list)):
                result[key] = normalize_paths_in_config(value)
            else:
                result[key] = value
        return result
    if isinstance(config, list):
        return [normalize_paths_in_config(item) for item in config]
    return config
