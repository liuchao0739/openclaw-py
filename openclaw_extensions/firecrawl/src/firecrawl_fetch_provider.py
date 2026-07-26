"""Firecrawl provider module implements model/runtime integration."""

from __future__ import annotations

from typing import Any

from openclaw.agents.tools.common import read_positive_integer_param
from openclaw.plugin_sdk.provider_enable_config import enable_plugin_in_config
from openclaw_extensions.firecrawl.src.firecrawl_client import run_firecrawl_scrape
from openclaw_extensions.firecrawl.src.firecrawl_fetch_provider_shared import (
    FIRECRAWL_WEB_FETCH_PROVIDER_SHARED,
)


def create_firecrawl_web_fetch_provider() -> dict[str, Any]:
    def apply_selection_config(config: dict[str, Any]) -> dict[str, Any]:
        return enable_plugin_in_config(config, "firecrawl")["config"]

    def create_tool(ctx: dict[str, Any]) -> dict[str, Any]:
        async def execute(args: dict[str, Any]) -> dict[str, Any]:
            url = args.get("url") if isinstance(args.get("url"), str) else ""
            extract_mode = "text" if args.get("extractMode") == "text" else "markdown"
            max_chars = read_positive_integer_param(args, "maxChars")
            proxy = (
                args.get("proxy")
                if args.get("proxy") in {"basic", "stealth", "auto"}
                else None
            )
            store_in_cache = (
                args.get("storeInCache") if isinstance(args.get("storeInCache"), bool) else None
            )
            scrape_params: dict[str, Any] = {
                "cfg": ctx.get("config"),
                "url": url,
                "extractMode": extract_mode,
                "access": "keyless",
                "maxChars": max_chars,
            }
            if proxy:
                scrape_params["proxy"] = proxy
            if store_in_cache is not None:
                scrape_params["storeInCache"] = store_in_cache
            return await run_firecrawl_scrape(scrape_params)

        return {
            "description": "Fetch a page using Firecrawl.",
            "parameters": {},
            "execute": execute,
        }

    return {
        **FIRECRAWL_WEB_FETCH_PROVIDER_SHARED,
        "apply_selection_config": apply_selection_config,
        "create_tool": create_tool,
    }
