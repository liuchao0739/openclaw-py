"""Message CLI command registrations — broadcast, poll, permissions, search, reactions, pins, send."""

from __future__ import annotations

from typing import Any

from openclaw.cli.program.message.helpers import MessageCliHelpers, collect_option

CHANNEL_TARGETS_DESCRIPTION = "Channel targets (e.g., telegram:12345 discord:98765)"


def register_message_broadcast_command(message_app: Any, helpers: MessageCliHelpers) -> None:
    """Register `message broadcast` for sending one payload to multiple channel targets."""
    try:
        import typer

        @message_app.command("broadcast")
        def broadcast(
            targets: list[str] = typer.Option(..., "--targets"),
            text: str | None = typer.Option(None, "--message"),
            media: str | None = typer.Option(None, "--media"),
        ) -> None:
            """Broadcast a message to multiple targets."""
            import asyncio

            asyncio.run(helpers.run_message_action("broadcast", {
                "targets": targets, "message": text, "media": media,
            }))
    except ImportError:
        pass


def register_message_poll_command(message_app: Any, helpers: MessageCliHelpers) -> None:
    """Register `message poll` for channel-backed poll creation."""
    try:
        import typer

        @message_app.command("poll")
        def poll(
            question: str = typer.Option(..., "--poll-question"),
            options: list[str] = typer.Option([], "--poll-option"),
            multi: bool = typer.Option(False, "--poll-multi"),
            message: str | None = typer.Option(None, "-m", "--message"),
            silent: bool = typer.Option(False, "--silent"),
        ) -> None:
            """Send a poll."""
            import asyncio

            asyncio.run(helpers.run_message_action("poll", {
                "question": question, "options": options, "multi": multi,
                "message": message, "silent": silent,
            }))
    except ImportError:
        pass


def register_message_permissions_command(message_app: Any, helpers: MessageCliHelpers) -> None:
    """Register the channel permissions inspection command."""
    try:
        import typer

        @message_app.command("permissions")
        def permissions() -> None:
            """Fetch channel permissions."""
            import asyncio

            asyncio.run(helpers.run_message_action("permissions", {}))
    except ImportError:
        pass


def register_message_search_command(message_app: Any, helpers: MessageCliHelpers) -> None:
    """Register Discord message search command."""
    try:
        import typer

        @message_app.command("search")
        def search(
            guild_id: str = typer.Option(..., "--guild-id"),
            query: str = typer.Option(..., "--query"),
            channel_id: str | None = typer.Option(None, "--channel-id"),
            limit: int | None = typer.Option(None, "--limit"),
        ) -> None:
            """Search Discord messages."""
            import asyncio

            asyncio.run(helpers.run_message_action("search", {
                "guildId": guild_id, "query": query,
                "channelId": channel_id, "limit": limit,
            }))
    except ImportError:
        pass
