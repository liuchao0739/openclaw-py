from __future__ import annotations

from typing import Any

try:
    import typer
except ImportError:
    typer = None

nodes_app = typer.Typer(help="Nodes management commands") if typer else None


def register_nodes_cli(app: Any) -> None:
    if not typer:
        return
    app.add_typer(nodes_app, name="nodes")

    @nodes_app.command("list")
    def nodes_list() -> None:
        print("Nodes: (not yet implemented)")

    @nodes_app.command("camera")
    def nodes_camera() -> None:
        print("Nodes camera: (not yet implemented)")

    @nodes_app.command("screen")
    def nodes_screen() -> None:
        print("Nodes screen: (not yet implemented)")
