"""Legacy daemon command registration."""

from __future__ import annotations

from typing import Any


def register_daemon_cli(app: Any) -> None:
    """Register the legacy daemon command group with a typer app.

    This is a stub that registers the daemon command group.
    Full subcommand implementations are deferred.
    """
    try:
        import typer

        daemon_app = typer.Typer(help="Manage the Gateway service (launchd/systemd/schtasks)")
        app.add_typer(daemon_app, name="daemon")

        @daemon_app.command("status")
        def daemon_status() -> None:
            """Show service install status + probe connectivity."""
            print("Gateway service status: (not yet implemented)")

        @daemon_app.command("start")
        def daemon_start() -> None:
            """Start the Gateway service."""
            print("Starting Gateway service: (not yet implemented)")

        @daemon_app.command("stop")
        def daemon_stop() -> None:
            """Stop the Gateway service."""
            print("Stopping Gateway service: (not yet implemented)")

        @daemon_app.command("restart")
        def daemon_restart() -> None:
            """Restart the Gateway service."""
            print("Restarting Gateway service: (not yet implemented)")

        @daemon_app.command("install")
        def daemon_install() -> None:
            """Install the Gateway service."""
            print("Installing Gateway service: (not yet implemented)")

        @daemon_app.command("uninstall")
        def daemon_uninstall() -> None:
            """Uninstall the Gateway service."""
            print("Uninstalling Gateway service: (not yet implemented)")

    except ImportError:
        pass
