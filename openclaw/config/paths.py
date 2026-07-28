from __future__ import annotations

import os
import re
import sys
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from openclaw.infra.paths import (
    LEGACY_STATE_DIRNAMES,
    NEW_STATE_DIRNAME,
    resolve_new_state_dir,
    resolve_legacy_state_dirs,
    resolve_required_home_dir,
    resolve_user_path,
)

CONFIG_FILENAME = "openclaw.json"
LEGACY_CONFIG_FILENAMES = ("clawdbot.json",)
DEFAULT_GATEWAY_PORT = 18789
OAUTH_FILENAME = "oauth.json"

DEFAULT_MODEL_MAX_TOKENS = 8192

MISTRAL_SAFE_MAX_TOKENS_BY_MODEL: dict[str, int] = {
    "devstral-medium-latest": 32768,
    "magistral-small": 40000,
    "mistral-large-latest": 16384,
    "mistral-medium-2508": 8192,
    "mistral-small-latest": 16384,
    "pixtral-large-latest": 32768,
}

DEFAULT_MODEL_ALIASES: dict[str, str] = {
    "opus": "anthropic/claude-opus-4-8",
    "sonnet": "anthropic/claude-sonnet-4-6",
    "gpt": "openai/gpt-5.4",
    "gpt-mini": "openai/gpt-5.4-mini",
    "gpt-nano": "openai/gpt-5.4-nano",
    "gemini": "google/gemini-3.1-pro-preview",
    "gemini-flash": "google/gemini-3-flash-preview",
    "gemini-flash-lite": "google/gemini-3.1-flash-lite",
}


def resolve_is_nix_mode(env: Mapping[str, str] | None = None) -> bool:
    env_map = env if env is not None else os.environ
    return env_map.get("OPENCLAW_NIX_MODE") == "1"


is_nix_mode = resolve_is_nix_mode()


def env_homedir(env: Mapping[str, str] | None = None) -> Callable[[], str]:
    env_map = env if env is not None else os.environ
    return lambda: resolve_required_home_dir(env_map)


def resolve_state_dir(
    env: Mapping[str, str] | None = None,
    homedir: Callable[[], str] | None = None,
) -> str:
    env_map = env if env is not None else os.environ
    home_fn = homedir or env_homedir(env_map)
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


def normalize_state_dir_env(env: dict[str, str] | None = None) -> None:
    env_map = env if env is not None else os.environ
    home_fn = env_homedir(env_map)
    openclaw_override = (env_map.get("OPENCLAW_STATE_DIR") or "").strip()
    if openclaw_override:
        env_map["OPENCLAW_STATE_DIR"] = resolve_user_path(openclaw_override, env_map, home_fn)


def resolve_include_roots(
    env: Mapping[str, str] | None = None,
    homedir: Callable[[], str] | None = None,
) -> list[str]:
    env_map = env if env is not None else os.environ
    raw = (env_map.get("OPENCLAW_INCLUDE_ROOTS") or "").strip()
    if not raw:
        return []
    home_fn = homedir or env_homedir(env_map)
    seen: set[str] = set()
    roots: list[str] = []
    for entry in raw.split(os.pathsep):
        trimmed = entry.strip()
        if not trimmed:
            continue
        resolved = str(Path(resolve_user_path(trimmed, env_map, home_fn)).resolve())
        if not Path(resolved).is_absolute() or resolved in seen:
            continue
        seen.add(resolved)
        roots.append(resolved)
    return roots


STATE_DIR = resolve_state_dir()


def resolve_canonical_config_path(
    env: Mapping[str, str] | None = None,
    state_dir: str | None = None,
) -> str:
    env_map = env if env is not None else os.environ
    home_fn = env_homedir(env_map)
    override = (env_map.get("OPENCLAW_CONFIG_PATH") or "").strip()
    if override:
        return resolve_user_path(override, env_map, home_fn)
    sd = state_dir if state_dir is not None else resolve_state_dir(env_map, home_fn)
    return str(Path(sd) / CONFIG_FILENAME)


def resolve_default_config_candidates(
    env: Mapping[str, str] | None = None,
    homedir: Callable[[], str] | None = None,
) -> list[str]:
    env_map = env if env is not None else os.environ
    home_fn = homedir or env_homedir(env_map)
    effective_home = lambda: resolve_required_home_dir(env_map)
    explicit = (env_map.get("OPENCLAW_CONFIG_PATH") or "").strip()
    if explicit:
        return [resolve_user_path(explicit, env_map, effective_home)]
    candidates: list[str] = []
    openclaw_state_dir = (env_map.get("OPENCLAW_STATE_DIR") or "").strip()
    if openclaw_state_dir:
        resolved = resolve_user_path(openclaw_state_dir, env_map, effective_home)
        candidates.append(str(Path(resolved) / CONFIG_FILENAME))
        for name in LEGACY_CONFIG_FILENAMES:
            candidates.append(str(Path(resolved) / name))
    default_dirs = [resolve_new_state_dir(env_map, effective_home)]
    default_dirs.extend(resolve_legacy_state_dirs(env_map, effective_home))
    for dir_path in default_dirs:
        candidates.append(str(Path(dir_path) / CONFIG_FILENAME))
        for name in LEGACY_CONFIG_FILENAMES:
            candidates.append(str(Path(dir_path) / name))
    return candidates


def resolve_config_path_candidate(
    env: Mapping[str, str] | None = None,
    homedir: Callable[[], str] | None = None,
) -> str:
    env_map = env if env is not None else os.environ
    home_fn = homedir or env_homedir(env_map)
    if env_map.get("OPENCLAW_TEST_FAST") == "1":
        return resolve_canonical_config_path(env_map, resolve_state_dir(env_map, home_fn))
    candidates = resolve_default_config_candidates(env_map, home_fn)
    for candidate in candidates:
        try:
            if Path(candidate).exists():
                return candidate
        except OSError:
            continue
    return resolve_canonical_config_path(env_map, resolve_state_dir(env_map, home_fn))


def resolve_config_path(
    env: Mapping[str, str] | None = None,
    state_dir: str | None = None,
    homedir: Callable[[], str] | None = None,
) -> str:
    env_map = env if env is not None else os.environ
    home_fn = homedir or env_homedir(env_map)
    override = (env_map.get("OPENCLAW_CONFIG_PATH") or "").strip()
    if override:
        return resolve_user_path(override, env_map, home_fn)
    if env_map.get("OPENCLAW_TEST_FAST") == "1":
        sd = state_dir if state_dir is not None else resolve_state_dir(env_map, home_fn)
        return str(Path(sd) / CONFIG_FILENAME)
    state_override = (env_map.get("OPENCLAW_STATE_DIR") or "").strip()
    sd = state_dir if state_dir is not None else resolve_state_dir(env_map, home_fn)
    candidates = [str(Path(sd) / CONFIG_FILENAME)]
    for name in LEGACY_CONFIG_FILENAMES:
        candidates.append(str(Path(sd) / name))
    for candidate in candidates:
        try:
            if Path(candidate).exists():
                return candidate
        except OSError:
            continue
    if state_override:
        return str(Path(sd) / CONFIG_FILENAME)
    default_sd = resolve_state_dir(env_map, home_fn)
    if str(Path(sd).resolve()) == str(Path(default_sd).resolve()):
        return resolve_config_path_candidate(env_map, home_fn)
    return str(Path(sd) / CONFIG_FILENAME)


CONFIG_PATH = resolve_config_path_candidate()


def pin_runtime_paths(env: Mapping[str, str] | None = None) -> dict[str, str]:
    global is_nix_mode, STATE_DIR, CONFIG_PATH
    env_map = env if env is not None else os.environ
    normalize_state_dir_env(env_map)
    is_nix_mode = resolve_is_nix_mode(env_map)
    STATE_DIR = resolve_state_dir(env_map)
    CONFIG_PATH = resolve_config_path_candidate(env_map)
    return {"configPath": CONFIG_PATH, "stateDir": STATE_DIR}


def resolve_gateway_lock_dir(tmpdir: Callable[[], str] | None = None) -> str:
    import tempfile
    base = tmpdir() if tmpdir else tempfile.gettempdir()
    try:
        uid = os.getuid()
        suffix = f"openclaw-{uid}"
    except (AttributeError, OSError):
        suffix = "openclaw"
    return str(Path(base) / suffix)


def resolve_oauth_dir(
    env: Mapping[str, str] | None = None,
    state_dir: str | None = None,
) -> str:
    env_map = env if env is not None else os.environ
    home_fn = env_homedir(env_map)
    override = (env_map.get("OPENCLAW_OAUTH_DIR") or "").strip()
    if override:
        return resolve_user_path(override, env_map, home_fn)
    sd = state_dir if state_dir is not None else resolve_state_dir(env_map, home_fn)
    return str(Path(sd) / "credentials")


def resolve_oauth_path(
    env: Mapping[str, str] | None = None,
    state_dir: str | None = None,
) -> str:
    return str(Path(resolve_oauth_dir(env, state_dir)) / OAUTH_FILENAME)


def parse_gateway_port_env_value(raw: str | None) -> int | None:
    if not raw:
        return None
    trimmed = raw.strip()
    if not trimmed:
        return None
    if re.match(r"^\d+$", trimmed):
        port = int(trimmed)
        if 1 <= port <= 65535:
            return port
        return None
    m = re.match(r"^\[([^\]]+)\]:(\d+)$", trimmed)
    if m:
        port = int(m.group(2))
        if 1 <= port <= 65535:
            return port
        return None
    first_colon = trimmed.find(":")
    last_colon = trimmed.rfind(":")
    if first_colon <= 0 or first_colon != last_colon:
        return None
    suffix = trimmed[first_colon + 1:]
    if not re.match(r"^\d+$", suffix):
        return None
    port = int(suffix)
    if 1 <= port <= 65535:
        return port
    return None


def resolve_gateway_port(
    cfg: dict[str, Any] | None = None,
    env: Mapping[str, str] | None = None,
) -> int:
    env_map = env if env is not None else os.environ
    env_raw = (env_map.get("OPENCLAW_GATEWAY_PORT") or "").strip()
    env_port = parse_gateway_port_env_value(env_raw)
    if env_port is not None:
        return env_port
    config_port = (cfg or {}).get("gateway", {}).get("port")
    if isinstance(config_port, (int, float)) and config_port > 0:
        return int(config_port)
    return DEFAULT_GATEWAY_PORT
