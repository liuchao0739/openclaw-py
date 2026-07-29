from __future__ import annotations

from typing import Any

try:
    import typer
except ImportError:
    typer = None

webhooks_app = typer.Typer(help="Webhook management commands") if typer else None


def register_webhooks_cli(app: Any) -> None:
    if not typer:
        return
    app.add_typer(webhooks_app, name="webhooks")

    @webhooks_app.command("list")
    def webhooks_list() -> None:
        print("Webhooks: (not yet implemented)")

    @webhooks_app.command("add")
    def webhooks_add() -> None:
        print("Add webhook: (not yet implemented)")
