from __future__ import annotations

from typing import Any

try:
    import typer
except ImportError:
    typer = None

skills_app = typer.Typer(help="Skills management commands") if typer else None


def register_skills_cli(app: Any) -> None:
    if not typer:
        return
    app.add_typer(skills_app, name="skills")

    @skills_app.command("list")
    def skills_list() -> None:
        print("Skills: (not yet implemented)")

    @skills_app.command("install")
    def skills_install() -> None:
        print("Install skill: (not yet implemented)")
