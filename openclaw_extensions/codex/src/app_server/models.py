"""Codex app-server model listing."""

from __future__ import annotations

from typing import Any


async def list_codex_app_server_models(options: dict[str, Any] | None = None) -> dict[str, Any]:
    options = options or {}
    from openclaw_extensions.codex.src.app_server.shared_client import (
        create_isolated_codex_app_server_client,
    )

    client = await create_isolated_codex_app_server_client(
        startOptions=options.get("startOptions"),
        timeoutMs=options.get("timeoutMs"),
        authProfileId=None,
    )
    try:
        await client.request(
            "model/list",
            {
                "limit": options.get("limit"),
                "cursor": options.get("cursor"),
                "includeHidden": options.get("includeHidden"),
            },
            timeoutMs=options.get("timeoutMs"),
        )
        return {"models": []}
    finally:
        client.close()
