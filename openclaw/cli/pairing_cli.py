from __future__ import annotations

from typing import Any

try:
    import typer
except ImportError:
    typer = None

pairing_app = typer.Typer(help="Pairing commands") if typer else None


def register_pairing_cli(app: Any) -> None:
    if not typer:
        return
    app.add_typer(pairing_app, name="pairing")

    @pairing_app.command("start")
    def pairing_start() -> None:
        print("Start pairing: (not yet implemented)")

    @pairing_app.command("status")
    def pairing_status() -> None:
        print("Pairing status: (not yet implemented)")
