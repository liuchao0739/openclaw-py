from __future__ import annotations

from typing import Any

try:
    import typer
except ImportError:
    typer = None

devices_app = typer.Typer(help="Device management commands") if typer else None


def register_devices_cli(app: Any) -> None:
    if not typer:
        return
    app.add_typer(devices_app, name="devices")

    @devices_app.command("list")
    def devices_list() -> None:
        print("Devices: (not yet implemented)")

    @devices_app.command("pair")
    def devices_pair() -> None:
        print("Pair device: (not yet implemented)")
