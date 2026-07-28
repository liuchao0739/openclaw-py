from __future__ import annotations

import sys

from openclaw_extensions.codex_supervisor.src.mcp_server import serve_codex_supervisor_mcp


def _format_error_message(error: Exception) -> str:
    return str(error) if str(error) else repr(error)


if __name__ == "__main__":
    try:
        import asyncio

        asyncio.run(serve_codex_supervisor_mcp())
    except Exception as err:
        sys.stderr.write(f"codex-supervisor-serve: {_format_error_message(err)}\n")
        sys.exit(1)