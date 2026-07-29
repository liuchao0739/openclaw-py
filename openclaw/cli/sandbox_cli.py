from __future__ import annotations

from typing import Any

try:
    import typer
except ImportError:
    typer = None

sandbox_app = typer.Typer(help="Sandbox management commands") if typer else None


def register_sandbox_cli(app: Any) -> None:
    if not typer:
        return
    app.add_typer(sandbox_app, name="sandbox")

    @sandbox_app.command("status")
    def sandbox_status() -> None:
        print("Sandbox status: (not yet implemented)")
