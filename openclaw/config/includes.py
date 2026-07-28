from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any


INCLUDE_KEY = "$include"
ENV_VAR_PATTERN = re.compile(r"\$\{([^}]+)\}")


class ConfigIncludeError(Exception):
    pass


def is_record(value: Any) -> bool:
    return isinstance(value, dict)


def hash_config_include_raw(raw: str | None) -> str:
    if raw is None:
        raw = ""
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def resolve_config_include_write_path(params: dict[str, Any]) -> str:
    config_path = params.get("configPath", "")
    include_path = params.get("includePath", "")
    allowed_roots = params.get("allowedRoots", [])
    root_dir = os.path.dirname(config_path)
    if os.path.isabs(include_path):
        return include_path
    return os.path.normpath(os.path.join(root_dir, include_path))


def contains_config_include_directive(value: Any) -> bool:
    if isinstance(value, list):
        return any(contains_config_include_directive(item) for item in value)
    if not isinstance(value, dict):
        return False
    return INCLUDE_KEY in value or any(
        contains_config_include_directive(item) for item in value.values()
    )


def get_single_top_level_include_target(
    snapshot: dict[str, Any], key: str
) -> str | None:
    if not is_record(snapshot.get("parsed")):
        return None
    authored_section = snapshot["parsed"].get(key)
    if not is_record(authored_section):
        return None
    keys = list(authored_section.keys())
    include_value = authored_section.get(INCLUDE_KEY)
    if len(keys) != 1 or not isinstance(include_value, str):
        return None
    root_dir = os.path.dirname(snapshot.get("path", ""))
    return os.path.normpath(
        include_value
        if os.path.isabs(include_value)
        else os.path.join(root_dir, include_value)
    )
