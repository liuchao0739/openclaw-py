from __future__ import annotations

from typing import Any

try:
    import typer
except ImportError:
    typer = None

docs_app = typer.Typer(help="Documentation commands") if typer else None


def register_docs_cli(app: Any) -> None:
    if not typer:
        return
    app.add_typer(docs_app, name="docs")

    @docs_app.command("open")
    def docs_open() -> None:
        print("Open docs: (not yet implemented)")
