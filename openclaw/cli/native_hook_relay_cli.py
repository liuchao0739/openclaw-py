from __future__ import annotations

from typing import Any

try:
    import typer
except ImportError:
    typer = None

native_hook_relay_app = typer.Typer(help="Native hook relay commands") if typer else None


def register_native_hook_relay_cli(app: Any) -> None:
    if not typer:
        return
    app.add_typer(native_hook_relay_app, name="native-hook-relay")

    @native_hook_relay_app.command("status")
    def native_hook_relay_status() -> None:
        print("Native hook relay status: (not yet implemented)")
