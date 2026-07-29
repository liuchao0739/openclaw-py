from __future__ import annotations

from typing import Any

try:
    import typer
except ImportError:
    typer = None

channels_app = typer.Typer(help="Channel management commands") if typer else None


def register_channels_cli(app: Any) -> None:
    if not typer:
        return
    app.add_typer(channels_app, name="channels")

    @channels_app.command("list")
    def channels_list() -> None:
        print("Channels: (not yet implemented)")

    @channels_app.command("add")
    def channels_add() -> None:
        print("Add channel: (not yet implemented)")

    @channels_app.command("remove")
    def channels_remove() -> None:
        print("Remove channel: (not yet implemented)")

    @channels_app.command("status")
    def channels_status() -> None:
        print("Channel status: (not yet implemented)")
