from __future__ import annotations

from typing import Any

try:
    import typer
except ImportError:
    typer = None

completion_app = typer.Typer(help="Shell completion commands") if typer else None


def register_completion_cli(app: Any) -> None:
    if not typer:
        return
    app.add_typer(completion_app, name="completion")

    @completion_app.command("install")
    def completion_install(shell: str = "bash") -> None:
        print(f"Install completion for {shell}: (not yet implemented)")

    @completion_app.command("uninstall")
    def completion_uninstall(shell: str = "bash") -> None:
        print(f"Uninstall completion for {shell}: (not yet implemented)")
