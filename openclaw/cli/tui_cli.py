from __future__ import annotations

from typing import Any

try:
    import typer
except ImportError:
    typer = None

tui_app = typer.Typer(help="TUI commands") if typer else None


def register_tui_cli(app: Any) -> None:
    if not typer:
        return
    app.add_typer(tui_app, name="tui")

    @tui_app.command("launch")
    def tui_launch() -> None:
        print("Launch TUI: (not yet implemented)")
