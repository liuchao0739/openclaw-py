"""Proxy capture path helpers resolve certificate artifacts.

Mirrors src/proxy-capture/paths.ts.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Mapping


def _resolve_state_dir(env: Mapping[str, str] | None = None) -> str:
    """Resolve the OpenClaw state directory from env."""
    if env is None:
        env = os.environ
    return env.get("OPENCLAW_STATE_DIR") or str(Path.home() / ".openclaw")


def _resolve_debug_proxy_root_dir(env: Mapping[str, str] | None = None) -> str:
    """Resolve the debug proxy root directory."""
    return str(Path(_resolve_state_dir(env)) / "debug-proxy")


def resolve_debug_proxy_db_path(env: Mapping[str, str] | None = None) -> str:
    """Resolve the debug proxy capture database path.

    Deprecated: capture storage now lives in the shared state database.
    """
    return str(Path(_resolve_debug_proxy_root_dir(env)) / "capture.sqlite")


def resolve_debug_proxy_blob_dir(env: Mapping[str, str] | None = None) -> str:
    """Resolve the debug proxy blob directory.

    Deprecated: capture payloads now live in the shared state database.
    """
    return str(Path(_resolve_debug_proxy_root_dir(env)) / "blobs")


def resolve_debug_proxy_cert_dir(env: Mapping[str, str] | None = None) -> str:
    """Resolve the debug proxy certificate directory."""
    return str(Path(_resolve_debug_proxy_root_dir(env)) / "certs")
