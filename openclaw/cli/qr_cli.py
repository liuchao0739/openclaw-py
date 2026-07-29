from __future__ import annotations

from typing import Any

try:
    import typer
except ImportError:
    typer = None

qr_app = typer.Typer(help="QR code commands") if typer else None


def register_qr_cli(app: Any) -> None:
    if not typer:
        return
    app.add_typer(qr_app, name="qr")

    @qr_app.command("generate")
    def qr_generate() -> None:
        print("Generate QR code: (not yet implemented)")
