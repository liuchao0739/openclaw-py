from __future__ import annotations

import json
import os
from typing import Any


def is_plain_object(value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    for key in value:
        if not isinstance(key, str):
            return False
    return True


def is_record(value: Any) -> bool:
    return isinstance(value, dict)


def get_prototype_keys(obj: Any) -> list[str]:
    if not isinstance(obj, dict):
        return []
    return list(obj.keys())


def has_own(obj: dict, key: str) -> bool:
    return key in obj


def deep_merge(base: dict, override: dict) -> dict:
    result = dict(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def pick_properties(obj: dict, keys: list[str]) -> dict:
    return {k: obj[k] for k in keys if k in obj}


def omit_properties(obj: dict, keys: list[str]) -> dict:
    return {k: v for k, v in obj.items() if k not in keys}


def parse_json_with_json5_fallback(raw: str) -> Any:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        try:
            import re
            cleaned = re.sub(r"//.*$", "", raw, flags=re.MULTILINE)
            cleaned = re.sub(r"/\*.*?\*/", "", cleaned, flags=re.DOTALL)
            return json.loads(cleaned)
        except (json.JSONDecodeError, Exception):
            raise ValueError("Failed to parse JSON/JSON5")
