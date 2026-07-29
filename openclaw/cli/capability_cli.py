from __future__ import annotations

from typing import Any

try:
    import typer
except ImportError:
    typer = None

capability_app = typer.Typer(help="Capability management commands") if typer else None


def register_capability_cli(app: Any) -> None:
    if not typer:
        return
    app.add_typer(capability_app, name="capability")

    @capability_app.command("list")
    def capability_list() -> None:
        print("Capabilities: (not yet implemented)")
