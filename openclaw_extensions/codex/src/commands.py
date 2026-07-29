from typing import Optional

from .app_server.capabilities import describe_control_failure
from .command_formatters import format_codex_display_text


def create_codex_command(options: dict) -> dict:
    def _handler(ctx):
        return handle_codex_command(ctx, options)

    return {
        "name": "codex",
        "description": "Inspect and control the Codex app-server harness",
        "ownership": "reserved",
        "agentPromptGuidance": [
            {
                "text": "Native Codex app-server plugin is available (`/codex ...`). For Codex bind/control/thread/resume/steer/stop requests, prefer `/codex bind`, `/codex threads`, `/codex resume`, `/codex steer`, and `/codex stop` over ACP. When OpenClaw sandboxing is active, native Codex execution modes are unavailable; use normal Codex harness turns.",
                "surfaces": ["openclaw_main"],
            },
            {
                "text": "Use ACP for Codex only when the user explicitly asks for ACP/acpx or wants to test the ACP path.",
                "surfaces": ["openclaw_main"],
            },
        ],
        "acceptsArgs": True,
        "requireAuth": True,
        "handler": _handler,
    }


async def handle_codex_command(ctx: dict, options: Optional[dict] = None):
    options = options or {}
    load_subcommand_handler = options.get("loadSubcommandHandler")
    subcommand_options = {k: v for k, v in options.items() if k != "loadSubcommandHandler"}
    try:
        if load_subcommand_handler:
            handle_codex_subcommand = await load_subcommand_handler()
        else:
            handle_codex_subcommand = await _load_default_codex_subcommand_handler()
        return await handle_codex_subcommand(ctx, subcommand_options)
    except Exception as error:
        return {"text": f"Codex command failed: {format_codex_display_text(describe_control_failure(error))}"}


async def _load_default_codex_subcommand_handler():
    from .command_handlers import handle_codex_subcommand

    return handle_codex_subcommand
