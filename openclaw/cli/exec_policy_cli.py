from __future__ import annotations

from typing import Any

try:
    import typer
except ImportError:
    typer = None

exec_policy_app = typer.Typer(help="Exec policy commands") if typer else None


def register_exec_policy_cli(app: Any) -> None:
    if not typer:
        return
    app.add_typer(exec_policy_app, name="exec-policy")

    @exec_policy_app.command("show")
    def exec_policy_show() -> None:
        print("Exec policy: (not yet implemented)")
