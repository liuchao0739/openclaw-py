from __future__ import annotations

from typing import Any

try:
    import typer
except ImportError:
    typer = None

hooks_app = typer.Typer(help="Hook management commands") if typer else None


def register_hooks_cli(app: Any) -> None:
    if not typer:
        return
    app.add_typer(hooks_app, name="hooks")

    @hooks_app.command("list")
    def hooks_list() -> None:
        print("Hooks: (not yet implemented)")

    @hooks_app.command("add")
    def hooks_add() -> None:
        print("Add hook: (not yet implemented)")
