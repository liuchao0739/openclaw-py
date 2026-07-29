from __future__ import annotations

from typing import Any

try:
    import typer
except ImportError:
    typer = None

system_app = typer.Typer(help="System management commands") if typer else None


def register_system_cli(app: Any) -> None:
    if not typer:
        return
    app.add_typer(system_app, name="system")

    @system_app.command("info")
    def system_info() -> None:
        print("System info: (not yet implemented)")

    @system_app.command("health")
    def system_health() -> None:
        print("System health: (not yet implemented)")
