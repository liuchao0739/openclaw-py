from __future__ import annotations

from typing import Any

try:
    import typer
except ImportError:
    typer = None

cron_app = typer.Typer(help="Cron job management commands") if typer else None


def register_cron_cli(app: Any) -> None:
    if not typer:
        return
    app.add_typer(cron_app, name="cron")

    @cron_app.command("list")
    def cron_list() -> None:
        print("Cron jobs: (not yet implemented)")

    @cron_app.command("add")
    def cron_add() -> None:
        print("Add cron job: (not yet implemented)")

    @cron_app.command("remove")
    def cron_remove() -> None:
        print("Remove cron job: (not yet implemented)")
