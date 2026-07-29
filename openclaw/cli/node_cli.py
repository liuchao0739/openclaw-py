from __future__ import annotations

from typing import Any

try:
    import typer
except ImportError:
    typer = None

node_app = typer.Typer(help="Node management commands") if typer else None


def register_node_cli(app: Any) -> None:
    if not typer:
        return
    app.add_typer(node_app, name="node")

    @node_app.command("status")
    def node_status() -> None:
        print("Node status: (not yet implemented)")
