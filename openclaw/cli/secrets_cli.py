from __future__ import annotations

from typing import Any

try:
    import typer
except ImportError:
    typer = None

secrets_app = typer.Typer(help="Secret management commands") if typer else None


def register_secrets_cli(app: Any) -> None:
    if not typer:
        return
    app.add_typer(secrets_app, name="secrets")

    @secrets_app.command("list")
    def secrets_list() -> None:
        print("Secrets: (not yet implemented)")

    @secrets_app.command("set")
    def secrets_set() -> None:
        print("Set secret: (not yet implemented)")

    @secrets_app.command("get")
    def secrets_get() -> None:
        print("Get secret: (not yet implemented)")
