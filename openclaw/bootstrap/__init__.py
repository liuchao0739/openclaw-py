"""Bootstrap — CA certificate and startup environment resolution."""

from openclaw.bootstrap.node_extra_ca_certs import (
    is_node_version_manager_runtime,
    resolve_auto_node_extra_ca_certs,
    resolve_linux_system_ca_bundle,
)
from openclaw.bootstrap.node_startup_env import resolve_node_startup_tls_environment

__all__ = [
    "is_node_version_manager_runtime",
    "resolve_auto_node_extra_ca_certs",
    "resolve_linux_system_ca_bundle",
    "resolve_node_startup_tls_environment",
]
