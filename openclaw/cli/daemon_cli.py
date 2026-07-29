from __future__ import annotations

from typing import Any

try:
    import typer
except ImportError:
    typer = None

daemon_app = typer.Typer(help="Daemon management commands") if typer else None


def register_daemon_cli(app: Any) -> None:
    if not typer:
        return
    app.add_typer(daemon_app, name="daemon")

    @daemon_app.command("start")
    def daemon_start() -> None:
        print("Start daemon: (not yet implemented)")

    @daemon_app.command("stop")
    def daemon_stop() -> None:
        print("Stop daemon: (not yet implemented)")

    @daemon_app.command("status")
    def daemon_status() -> None:
        print("Daemon status: (not yet implemented)")
