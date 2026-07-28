from __future__ import annotations

import os
from collections.abc import Callable
from typing import Any

from openclaw_extensions.codex_supervisor.src.config import load_codex_supervisor_endpoints
from openclaw_extensions.codex_supervisor.src.mcp_tools import (
    RAW_TRANSCRIPTS_ENV,
    WRITE_CONTROLS_ENV,
    register_codex_supervisor_mcp_tools,
)
from openclaw_extensions.codex_supervisor.src.supervisor import CodexSupervisor

VERSION = "0.1.0"


def _route_logs_to_stderr() -> None:
    import sys

    async def _noop_log(*args: Any) -> None:
        sys.stderr.write(" ".join(str(a) for a in args) + "\n")

    import logging

    logger = logging.getLogger("mcp")
    logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.handlers = [handler]


def _raw_transcript_reads_allowed() -> bool:
    return os.environ.get(RAW_TRANSCRIPTS_ENV) == "1"


def _write_controls_allowed() -> bool:
    return os.environ.get(WRITE_CONTROLS_ENV) == "1"


CodexSupervisorMcpServeOptions = dict[str, Any]


def create_codex_supervisor_mcp_server(
    opts: CodexSupervisorMcpServeOptions | None = None,
) -> dict[str, Any]:
    options = opts or {}
    supervisor = options.get("supervisor")
    if supervisor is None:
        supervisor = CodexSupervisor(load_codex_supervisor_endpoints())

    tool_options = options.get("toolOptions") or {}

    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError:
        try:
            from mcp.server import Server
        except ImportError:
            raise RuntimeError(
                "MCP SDK is required for codex-supervisor MCP server. "
                "Install it with: pip install mcp"
            )

    server = Server("openclaw-codex-supervisor")

    register_codex_supervisor_mcp_tools(server, supervisor, tool_options)

    async def _close() -> None:
        await supervisor.close()

    return {"server": server, "supervisor": supervisor, "close": _close}


async def serve_codex_supervisor_mcp(
    opts: CodexSupervisorMcpServeOptions | None = None,
) -> None:
    _route_logs_to_stderr()
    result = create_codex_supervisor_mcp_server(opts)
    server = result["server"]
    close_fn = result["close"]

    shutting_down = False

    async def _shutdown() -> None:
        nonlocal shutting_down
        if shutting_down:
            return
        shutting_down = True
        await close_fn()

    import asyncio

    try:
        async with asyncio.Event() as done_event:
            await done_event.wait()
    except KeyboardInterrupt:
        pass
    finally:
        await _shutdown()