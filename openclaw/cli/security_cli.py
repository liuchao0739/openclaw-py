from __future__ import annotations

from typing import Any

try:
    import typer
except ImportError:
    typer = None

security_app = typer.Typer(help="Security management commands") if typer else None


def register_security_cli(app: Any) -> None:
    if not typer:
        return
    app.add_typer(security_app, name="security")

    @security_app.command("scan")
    def security_scan() -> None:
        print("Security scan: (not yet implemented)")

    @security_app.command("audit")
    def security_audit() -> None:
        print("Security audit: (not yet implemented)")
