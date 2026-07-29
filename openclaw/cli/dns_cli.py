from __future__ import annotations

from typing import Any

try:
    import typer
except ImportError:
    typer = None

dns_app = typer.Typer(help="DNS management commands") if typer else None


def register_dns_cli(app: Any) -> None:
    if not typer:
        return
    app.add_typer(dns_app, name="dns")

    @dns_app.command("status")
    def dns_status() -> None:
        print("DNS status: (not yet implemented)")
