from __future__ import annotations

from typing import Any


async def execute_gateway_rpc(url: str, payload: dict, opts: dict | None = None) -> Any:
    import aiohttp

    options = opts or {}
    timeout = options.get("timeout", 30)
    headers = options.get("headers", {})
    if options.get("token"):
        headers["Authorization"] = f"Bearer {options['token']}"
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload, headers=headers, timeout=timeout) as resp:
            return await resp.json()
