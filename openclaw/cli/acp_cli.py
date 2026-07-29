from __future__ import annotations

from typing import Any

try:
    import typer
except ImportError:
    typer = None

acp_app = typer.Typer(help="ACP control plane commands") if typer else None


def register_acp_cli(app: Any) -> None:
    if not typer:
        return
    app.add_typer(acp_app, name="acp")

    @acp_app.command("status")
    def acp_status() -> None:
        print("ACP status: (not yet implemented)")

    @acp_app.command("list")
    def acp_list() -> None:
        print("ACP agents: (not yet implemented)")
