"""Commander/typer registration for foreground node host and node service lifecycle commands."""

from __future__ import annotations

from typing import Any


def _parse_port_option(value: Any, fallback: int) -> int | None:
    """Parse a port option, returning fallback for undefined, None for invalid."""
    if value is None:
        return fallback
    try:
        port = int(value)
        return port if 1 <= port <= 65535 else None
    except (ValueError, TypeError):
        return None


def register_node_cli(app: Any) -> None:
    """Register node host and service lifecycle commands with a typer app.

    This is a stub that registers the node command group.
    """
    try:
        import typer

        node_app = typer.Typer(help="Manage node host and node service lifecycle")
        app.add_typer(node_app, name="node")

        @node_app.command("host")
        def node_host() -> None:
            """Run the foreground node host."""
            print("Node host: (not yet implemented)")

        @node_app.command("status")
        def node_status() -> None:
            """Show node service status."""
            print("Node service status: (not yet implemented)")

        @node_app.command("install")
        def node_install() -> None:
            """Install the node service."""
            print("Install node service: (not yet implemented)")

        @node_app.command("start")
        def node_start() -> None:
            """Start the node service."""
            print("Start node service: (not yet implemented)")

        @node_app.command("stop")
        def node_stop() -> None:
            """Stop the node service."""
            print("Stop node service: (not yet implemented)")

        @node_app.command("restart")
        def node_restart() -> None:
            """Restart the node service."""
            print("Restart node service: (not yet implemented)")

        @node_app.command("uninstall")
        def node_uninstall() -> None:
            """Uninstall the node service."""
            print("Uninstall node service: (not yet implemented)")

    except ImportError:
        pass
