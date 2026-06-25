"""Node CLI — daemon lifecycle and command registration."""

from openclaw.cli.node_cli.daemon import (
    DEFAULT_NODE_DAEMON_RUNTIME,
    is_node_daemon_runtime,
    run_node_daemon_install,
    run_node_daemon_restart,
    run_node_daemon_start,
    run_node_daemon_status,
    run_node_daemon_stop,
    run_node_daemon_uninstall,
)
from openclaw.cli.node_cli.register import register_node_cli

__all__ = [
    "DEFAULT_NODE_DAEMON_RUNTIME",
    "is_node_daemon_runtime",
    "register_node_cli",
    "run_node_daemon_install",
    "run_node_daemon_restart",
    "run_node_daemon_start",
    "run_node_daemon_status",
    "run_node_daemon_stop",
    "run_node_daemon_uninstall",
]
