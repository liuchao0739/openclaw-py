from __future__ import annotations

from typing import Any

try:
    import typer
except ImportError:
    typer = None

config_app = typer.Typer(help="Configuration management commands") if typer else None


def register_config_cli(app: Any) -> None:
    if not typer:
        return
    app.add_typer(config_app, name="config")

    @config_app.command("get")
    def config_get(key: str = "") -> None:
        print(f"Config get {key}: (not yet implemented)")

    @config_app.command("set")
    def config_set(key: str = "", value: str = "") -> None:
        print(f"Config set {key}={value}: (not yet implemented)")

    @config_app.command("list")
    def config_list() -> None:
        print("Config list: (not yet implemented)")

    @config_app.command("unset")
    def config_unset(key: str = "") -> None:
        print(f"Config unset {key}: (not yet implemented)")
