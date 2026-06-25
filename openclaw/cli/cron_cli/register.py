"""Top-level cron CLI registration and subcommand wiring.

Uses typer for CLI command registration (Python equivalent of commander).
"""

from __future__ import annotations

from typing import Any


def register_cron_cli(app: Any) -> None:
    """Register cron subcommands with a typer app.

    This is a stub that registers the cron command group.
    Full subcommand implementations are deferred until the CLI layer is ported.
    """
    try:
        import typer

        cron_app = typer.Typer(help="Manage cron jobs (via Gateway)")
        app.add_typer(cron_app, name="cron")

        @cron_app.command("status")
        def cron_status() -> None:
            """Show cron job service status."""
            print("Cron service status: (not yet implemented)")

        @cron_app.command("list")
        def cron_list() -> None:
            """List configured cron jobs."""
            print("Cron jobs: (not yet implemented)")

        @cron_app.command("add")
        def cron_add() -> None:
            """Add a new cron job."""
            print("Add cron job: (not yet implemented)")

        @cron_app.command("edit")
        def cron_edit() -> None:
            """Edit an existing cron job."""
            print("Edit cron job: (not yet implemented)")

        @cron_app.command("remove")
        def cron_remove() -> None:
            """Remove a cron job."""
            print("Remove cron job: (not yet implemented)")

    except ImportError:
        pass
