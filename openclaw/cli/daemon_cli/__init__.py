"""Daemon CLI — Gateway service lifecycle commands."""

from openclaw.cli.daemon_cli.gateway_token_drift import (
    resolve_gateway_token_for_drift_check,
)
from openclaw.cli.daemon_cli.register import register_daemon_cli
from openclaw.cli.daemon_cli.status import run_daemon_status
from openclaw.cli.daemon_cli.types import (
    DaemonInstallOptions,
    DaemonLifecycleOptions,
    DaemonStatusOptions,
    GatewayRpcOpts,
)

__all__ = [
    "DaemonInstallOptions",
    "DaemonLifecycleOptions",
    "DaemonStatusOptions",
    "GatewayRpcOpts",
    "register_daemon_cli",
    "resolve_gateway_token_for_drift_check",
    "run_daemon_status",
]
