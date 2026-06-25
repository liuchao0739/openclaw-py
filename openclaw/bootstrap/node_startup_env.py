"""Builds startup environment variables for subprocess launches."""

from __future__ import annotations

import sys
from typing import Any, Callable

from openclaw.bootstrap.node_extra_ca_certs import (
    EnvMap,
    resolve_auto_node_extra_ca_certs,
)


def resolve_node_startup_tls_environment(
    env: EnvMap | None = None,
    platform: str | None = None,
    exec_path: str | None = None,
    include_darwin_defaults: bool = True,
    access_sync: Callable[..., None] | None = None,
) -> dict[str, str | None]:
    """Resolve NODE_* TLS env values without overwriting user-provided settings."""
    env_map = env if env is not None else dict(__import__("os").environ)
    plat = platform or sys.platform

    existing_ca_certs = env_map.get("NODE_EXTRA_CA_CERTS")
    if existing_ca_certs and existing_ca_certs.strip():
        node_extra_ca_certs = existing_ca_certs
    elif plat == "darwin" and include_darwin_defaults:
        node_extra_ca_certs = "/etc/ssl/cert.pem"
    else:
        node_extra_ca_certs = resolve_auto_node_extra_ca_certs(
            env_map, plat, exec_path, access_sync
        )

    existing_system_ca = env_map.get("NODE_USE_SYSTEM_CA")
    if existing_system_ca is not None:
        node_use_system_ca = existing_system_ca
    elif plat == "darwin" and include_darwin_defaults:
        node_use_system_ca = "1"
    else:
        node_use_system_ca = None

    return {
        "NODE_EXTRA_CA_CERTS": node_extra_ca_certs,
        "NODE_USE_SYSTEM_CA": node_use_system_ca,
    }
