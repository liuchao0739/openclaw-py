"""OpenClaw CLI entry point."""

from __future__ import annotations

import typer

app = typer.Typer(
    name="openclaw-py",
    help="OpenClaw Python — multi-channel AI gateway",
    no_args_is_help=True,
)


@app.command()
def version() -> None:
    """Show version."""
    from openclaw import __version__

    typer.echo(f"openclaw-py {__version__}")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
