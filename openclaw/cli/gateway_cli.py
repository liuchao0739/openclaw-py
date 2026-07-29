from __future__ import annotations

from typing import Any

try:
    import typer
except ImportError:
    typer = None

gateway_cli_app = typer.Typer(help="Gateway CLI commands") if typer else None


def register_gateway_cli(app: Any) -> None:
    if not typer:
        return
    app.add_typer(gateway_cli_app, name="gateway-cli")

    @gateway_cli_app.command("call")
    def gateway_call() -> None:
        print("Gateway call: (not yet implemented)")

    @gateway_cli_app.command("discover")
    def gateway_discover() -> None:
        print("Gateway discover: (not yet implemented)")
