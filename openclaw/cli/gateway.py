"""Gateway CLI commands."""

from __future__ import annotations

import typer
import uvicorn

from openclaw.config.loader import load_config

gateway_app = typer.Typer(help="Gateway server commands")


@gateway_app.command("start")
def start(
    host: str = typer.Option("127.0.0.1", help="Bind host"),
    port: int | None = typer.Option(None, help="Bind port"),
) -> None:
    """Start the OpenClaw gateway HTTP server."""
    config = load_config()
    resolved_port = port or (config.gateway.resolved_port() if config.gateway else 18789)
    typer.echo(f"Starting gateway on {host}:{resolved_port}")
    uvicorn.run("openclaw.gateway.server:app", host=host, port=resolved_port, reload=False)
