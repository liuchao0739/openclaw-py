from __future__ import annotations

from typing import Any

try:
    import typer
except ImportError:
    typer = None

clawbot_app = typer.Typer(help="ClawBot management commands") if typer else None


def register_clawbot_cli(app: Any) -> None:
    if not typer:
        return
    app.add_typer(clawbot_app, name="clawbot")

    @clawbot_app.command("status")
    def clawbot_status() -> None:
        print("ClawBot status: (not yet implemented)")
