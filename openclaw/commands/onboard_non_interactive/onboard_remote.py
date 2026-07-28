from __future__ import annotations

from typing import Any


async def onboard_remote_command(
    opts: dict[str, Any] | None = None,
    runtime: dict[str, Any] | None = None,
) -> dict[str, Any]:
    rt = runtime or {}
    options = opts or {}
    host = options.get("host", "")
    port = options.get("port", "8787")

    if rt.get("log"):
        rt["log"](f"Connecting to remote gateway at {host}:{port}")

    return {
        "ok": True,
        "host": host,
        "port": port,
    }
