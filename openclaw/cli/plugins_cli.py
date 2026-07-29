from __future__ import annotations

from typing import Any

try:
    import typer
except ImportError:
    typer = None

plugins_app = typer.Typer(help="Plugin management commands") if typer else None


def register_plugins_cli(app: Any) -> None:
    if not typer:
        return
    app.add_typer(plugins_app, name="plugins")

    @plugins_app.command("list")
    def plugins_list() -> None:
        print("Plugins: (not yet implemented)")

    @plugins_app.command("install")
    def plugins_install() -> None:
        print("Install plugin: (not yet implemented)")

    @plugins_app.command("uninstall")
    def plugins_uninstall() -> None:
        print("Uninstall plugin: (not yet implemented)")

    @plugins_app.command("search")
    def plugins_search() -> None:
        print("Search plugins: (not yet implemented)")
