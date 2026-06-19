"""Filesystem path resolution."""

from __future__ import annotations

import os
from collections.abc import Callable, Mapping
from pathlib import Path

LEGACY_STATE_DIRNAMES = (".clawdbot",)
NEW_STATE_DIRNAME = ".openclaw"
CONFIG_FILENAME = "openclaw.json"


def resolve_required_home_dir(
    env: Mapping[str, str] | None = None,
    homedir: Callable[[], str] | None = None,
) -> str:
    env_map = env if env is not None else os.environ
    override = (env_map.get("OPENCLAW_HOME") or "").strip()
    if override:
        return str(Path(override).expanduser())
    if homedir is not None:
        return homedir()
    return str(Path.home())


def resolve_user_path(
    raw: str,
    env: Mapping[str, str] | None = None,
    homedir: Callable[[], str] | None = None,
) -> str:
    expanded = str(Path(raw).expanduser())
    if expanded.startswith("~"):
        home = resolve_required_home_dir(env, homedir)
        return str(Path(home) / expanded.lstrip("~/"))
    return expanded


def resolve_new_state_dir(
    env: Mapping[str, str] | None = None,
    homedir: Callable[[], str] | None = None,
) -> str:
    home = resolve_required_home_dir(env, homedir)
    return str(Path(home) / NEW_STATE_DIRNAME)


def resolve_legacy_state_dirs(
    env: Mapping[str, str] | None = None,
    homedir: Callable[[], str] | None = None,
) -> list[str]:
    home = resolve_required_home_dir(env, homedir)
    return [str(Path(home) / name) for name in LEGACY_STATE_DIRNAMES]


def resolve_state_dir(
    env: Mapping[str, str] | None = None,
    homedir: Callable[[], str] | None = None,
) -> str:
    """Resolve mutable state directory. Default: ~/.openclaw"""
    env_map = env if env is not None else os.environ
    home_fn = homedir or (lambda: resolve_required_home_dir(env_map))

    override = (env_map.get("OPENCLAW_STATE_DIR") or "").strip()
    if override:
        return resolve_user_path(override, env_map, home_fn)

    new_dir = resolve_new_state_dir(env_map, home_fn)
    if env_map.get("OPENCLAW_TEST_FAST") == "1":
        return new_dir

    if Path(new_dir).exists():
        return new_dir

    for legacy in resolve_legacy_state_dirs(env_map, home_fn):
        if Path(legacy).exists():
            return legacy

    return new_dir


def resolve_config_path(
    env: Mapping[str, str] | None = None,
    homedir: Callable[[], str] | None = None,
) -> str:
    return str(Path(resolve_state_dir(env, homedir)) / CONFIG_FILENAME)
