from __future__ import annotations

from typing import Any

try:
    import typer
except ImportError:
    typer = None


def build_program() -> Any:
    if not typer:
        return None
    app = typer.Typer(name="openclaw", help="OpenClaw CLI", no_args_is_help=True)
    return app


def run_program(app: Any = None) -> None:
    if app is None:
        app = build_program()
    if app:
        app()


def register_program_commands(app: Any) -> None:
    from openclaw.cli.gateway import gateway_app
    if gateway_app:
        app.add_typer(gateway_app, name="gateway")
