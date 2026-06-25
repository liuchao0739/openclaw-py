"""Resolves additional CA certificate settings for child processes."""

from __future__ import annotations

import os
import sys
from typing import Any, Callable

LINUX_CA_BUNDLE_PATHS = (
    "/etc/ssl/certs/ca-certificates.crt",
    "/etc/pki/tls/certs/ca-bundle.crt",
    "/etc/ssl/ca-bundle.pem",
)

VERSION_MANAGER_PATH_MARKERS = (
    "/.nvm/",
    "/.fnm/",
    "/.local/share/fnm/",
    "/.volta/",
    "/.asdf/",
    "/.local/share/mise/",
    "/.n/",
    "/.nodenv/",
    "/.nodebrew/",
    "/nvs/",
    "/.nvs/",
)

EnvMap = dict[str, str | None]
AccessSyncFn = Callable[..., None]


def resolve_linux_system_ca_bundle(
    platform: str | None = None,
    access_sync: AccessSyncFn | None = None,
) -> str | None:
    """Resolve the first readable Linux CA bundle path."""
    plat = platform or sys.platform
    if plat != "linux":
        return None

    access = access_sync or _default_access_sync
    for candidate in LINUX_CA_BUNDLE_PATHS:
        try:
            access(candidate)
            return candidate
        except Exception:
            continue
    return None


def _default_access_sync(path: str) -> None:
    if not os.access(path, os.R_OK):
        raise FileNotFoundError(path)


def is_node_version_manager_runtime(
    env: EnvMap | None = None,
    exec_path: str | None = None,
) -> bool:
    """Check if the current runtime is managed by a Node version manager."""
    env_map = env if env is not None else dict(os.environ)
    exe = exec_path or sys.executable

    nvm_dir = env_map.get("NVM_DIR")
    if nvm_dir and nvm_dir.strip():
        return True

    return any(marker in exe for marker in VERSION_MANAGER_PATH_MARKERS)


def resolve_auto_node_extra_ca_certs(
    env: EnvMap | None = None,
    platform: str | None = None,
    exec_path: str | None = None,
    access_sync: AccessSyncFn | None = None,
) -> str | None:
    """Auto-resolve NODE_EXTRA_CA_CERTS for version-manager Node runtimes on Linux."""
    env_map = env if env is not None else dict(os.environ)

    existing = env_map.get("NODE_EXTRA_CA_CERTS")
    if existing and existing.strip():
        return None

    plat = platform or sys.platform
    exe = exec_path or sys.executable

    if plat != "linux" or not is_node_version_manager_runtime(env_map, exe):
        return None

    return resolve_linux_system_ca_bundle(plat, access_sync)
