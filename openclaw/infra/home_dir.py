from __future__ import annotations

import os
import re
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any


def _normalize(value: str | None) -> str | None:
    if value is None:
        return None
    trimmed = value.strip()
    if not trimmed or trimmed == "undefined" or trimmed == "null":
        return None
    return trimmed


def _normalize_safe(homedir: Callable[[], str]) -> str | None:
    try:
        return _normalize(homedir())
    except Exception:
        return None


def _resolve_termux_home(env: Mapping[str, str]) -> str | None:
    prefix = _normalize(env.get("PREFIX"))
    if not prefix or not _normalize(env.get("ANDROID_DATA")):
        return None
    normalized_prefix = prefix.replace("\\", "/")
    if not re.search(r"(?:^|/)com\.termux/files/usr/?$", normalized_prefix):
        return None
    return str(Path(prefix).resolve().parent / "home")


def _resolve_raw_os_home_dir(
    env: Mapping[str, str],
    homedir: Callable[[], str],
) -> str | None:
    return (
        _normalize(env.get("HOME"))
        or _normalize(env.get("USERPROFILE"))
        or _resolve_termux_home(env)
        or _normalize_safe(homedir)
    )


def _resolve_raw_home_dir(
    env: Mapping[str, str],
    homedir: Callable[[], str],
) -> str | None:
    explicit_home = _normalize(env.get("OPENCLAW_HOME"))
    if not explicit_home:
        return _resolve_raw_os_home_dir(env, homedir)
    if explicit_home == "~" or explicit_home.startswith("~/") or explicit_home.startswith("~\\"):
        fallback = _resolve_raw_os_home_dir(env, homedir)
        if fallback:
            return re.sub(r"^~(?=$|[/\\])", fallback, explicit_home)
        return None
    return explicit_home


def resolve_effective_home_dir(
    env: Mapping[str, str] | None = None,
    homedir: Callable[[], str] | None = None,
) -> str | None:
    env_map = env if env is not None else os.environ
    home_fn = homedir or os.path.expanduser
    raw = _resolve_raw_home_dir(env_map, home_fn)
    return str(Path(raw).resolve()) if raw else None


def resolve_os_home_dir(
    env: Mapping[str, str] | None = None,
    homedir: Callable[[], str] | None = None,
) -> str | None:
    env_map = env if env is not None else os.environ
    home_fn = homedir or os.path.expanduser
    raw = _resolve_raw_os_home_dir(env_map, home_fn)
    return str(Path(raw).resolve()) if raw else None


def resolve_required_home_dir(
    env: Mapping[str, str] | None = None,
    homedir: Callable[[], str] | None = None,
) -> str:
    env_map = env if env is not None else os.environ
    home_fn = homedir or os.path.expanduser
    return resolve_effective_home_dir(env_map, home_fn) or str(Path.cwd())


def resolve_required_os_home_dir(
    env: Mapping[str, str] | None = None,
    homedir: Callable[[], str] | None = None,
) -> str:
    env_map = env if env is not None else os.environ
    home_fn = homedir or os.path.expanduser
    return resolve_os_home_dir(env_map, home_fn) or str(Path.cwd())


def expand_home_prefix(
    input_path: str,
    opts: dict[str, Any] | None = None,
) -> str:
    if not input_path.startswith("~"):
        return input_path
    opts = opts or {}
    home = _normalize(opts.get("home"))
    if not home:
        env_map = opts.get("env") or os.environ
        home_fn = opts.get("homedir") or os.path.expanduser
        home = resolve_effective_home_dir(env_map, home_fn)
    if not home:
        return input_path
    return re.sub(r"^~(?=$|[/\\])", home, input_path)


def resolve_home_relative_path(
    input_path: str,
    opts: dict[str, Any] | None = None,
) -> str:
    trimmed = input_path.strip()
    if not trimmed:
        return trimmed
    opts = opts or {}
    if trimmed.startswith("~"):
        env_map = opts.get("env") or os.environ
        home_fn = opts.get("homedir") or os.path.expanduser
        expanded = expand_home_prefix(
            trimmed,
            {"home": resolve_required_home_dir(env_map, home_fn), "env": env_map, "homedir": home_fn},
        )
        return str(Path(expanded).resolve())
    return str(Path(trimmed).resolve())


def resolve_user_path(
    input_path: str,
    env: Mapping[str, str] | None = None,
    homedir: Callable[[], str] | None = None,
) -> str:
    return resolve_home_relative_path(input_path, {"env": env, "homedir": homedir})


def resolve_os_home_relative_path(
    input_path: str,
    opts: dict[str, Any] | None = None,
) -> str:
    trimmed = input_path.strip()
    if not trimmed:
        return trimmed
    opts = opts or {}
    if trimmed.startswith("~"):
        env_map = opts.get("env") or os.environ
        home_fn = opts.get("homedir") or os.path.expanduser
        expanded = expand_home_prefix(
            trimmed,
            {"home": resolve_required_os_home_dir(env_map, home_fn), "env": env_map, "homedir": home_fn},
        )
        return str(Path(expanded).resolve())
    return str(Path(trimmed).resolve())
