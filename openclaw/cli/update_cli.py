from __future__ import annotations

from typing import Any

try:
    import typer
except ImportError:
    typer = None

update_app = typer.Typer(help="Update management commands") if typer else None


def register_update_cli(app: Any) -> None:
    if not typer:
        return
    app.add_typer(update_app, name="update")

    @update_app.command("check")
    def update_check() -> None:
        print("Check for updates: (not yet implemented)")

    @update_app.command("apply")
    def update_apply() -> None:
        print("Apply updates: (not yet implemented)")
