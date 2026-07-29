from __future__ import annotations

from typing import Any

try:
    import typer
except ImportError:
    typer = None

models_app = typer.Typer(help="Model management commands") if typer else None


def register_models_cli(app: Any) -> None:
    if not typer:
        return
    app.add_typer(models_app, name="models")

    @models_app.command("list")
    def models_list() -> None:
        print("Models: (not yet implemented)")

    @models_app.command("set")
    def models_set() -> None:
        print("Set model: (not yet implemented)")
