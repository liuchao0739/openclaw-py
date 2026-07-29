from __future__ import annotations

from typing import Any

try:
    import typer
except ImportError:
    typer = None

directory_app = typer.Typer(help="Directory management commands") if typer else None


def register_directory_cli(app: Any) -> None:
    if not typer:
        return
    app.add_typer(directory_app, name="directory")

    @directory_app.command("list")
    def directory_list() -> None:
        print("Directory: (not yet implemented)")
