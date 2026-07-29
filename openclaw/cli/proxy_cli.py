from __future__ import annotations

from typing import Any

try:
    import typer
except ImportError:
    typer = None

proxy_app = typer.Typer(help="Proxy management commands") if typer else None


def register_proxy_cli(app: Any) -> None:
    if not typer:
        return
    app.add_typer(proxy_app, name="proxy")

    @proxy_app.command("status")
    def proxy_status() -> None:
        print("Proxy status: (not yet implemented)")
