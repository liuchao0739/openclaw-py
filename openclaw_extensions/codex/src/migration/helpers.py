import os
import re
from pathlib import Path

from openclaw.plugin_sdk.json_store import read_json_file_with_fallback
from openclaw.plugin_sdk.security_runtime import path_exists


async def exists(file_path: str) -> bool:
    return await path_exists(file_path)


async def is_directory(file_path) -> bool:
    if not file_path:
        return False
    try:
        return Path(file_path).is_dir()
    except OSError:
        return False


def resolve_user_home_dir() -> str:
    return os.environ.get("HOME", "").strip() or str(Path.home())


def resolve_home_path(value: str) -> str:
    if value == "~":
        return resolve_user_home_dir()
    if value.startswith("~/"):
        return str(Path(resolve_user_home_dir(), value[2:]))
    return str(Path(value).resolve())


def sanitize_name(value: str) -> str:
    sanitized = re.sub(r"[^a-z0-9._-]+", "-", value.strip().lower())
    sanitized = re.sub(r"^-+|-+$", "", sanitized)
    return sanitized[:64]


async def read_json_object(file_path) -> dict:
    if not file_path:
        return {}
    value = await read_json_file_with_fallback(file_path, {})
    return value if isinstance(value, dict) and not isinstance(value, list) else {}
