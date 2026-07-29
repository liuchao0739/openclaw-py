from __future__ import annotations

from typing import Any

try:
    import typer
except ImportError:
    typer = None

mcp_app = typer.Typer(help="MCP management commands") if typer else None


def register_mcp_cli(app: Any) -> None:
    if not typer:
        return
    app.add_typer(mcp_app, name="mcp")

    @mcp_app.command("list")
    def mcp_list() -> None:
        print("MCP servers: (not yet implemented)")
