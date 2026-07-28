"""Config evaluation helpers load dynamic config modules with guarded evaluation."""

from __future__ import annotations

import os
import platform
from typing import Any, Callable


def is_truthy(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return len(value.strip()) > 0
    return True


def resolve_config_path(config: Any, path_str: str) -> Any:
    parts = [p for p in path_str.split(".") if p]
    current = config
    for part in parts:
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current


def is_config_path_truthy_with_defaults(
    config: Any,
    path_str: str,
    defaults: dict[str, bool],
) -> bool:
    value = resolve_config_path(config, path_str)
    if value is None and path_str in defaults:
        return defaults.get(path_str, False)
    return is_truthy(value)


def resolve_runtime_platform() -> str:
    return platform.system().lower()


def has_binary(bin_name: str) -> bool:
    import shutil
    return shutil.which(bin_name) is not None
