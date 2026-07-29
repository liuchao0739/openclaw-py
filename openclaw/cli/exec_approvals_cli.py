from __future__ import annotations

from typing import Any

try:
    import typer
except ImportError:
    typer = None

exec_approvals_app = typer.Typer(help="Exec approval commands") if typer else None


def register_exec_approvals_cli(app: Any) -> None:
    if not typer:
        return
    app.add_typer(exec_approvals_app, name="exec-approvals")

    @exec_approvals_app.command("list")
    def exec_approvals_list() -> None:
        print("Exec approvals: (not yet implemented)")
