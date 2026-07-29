from typing import Any, Optional

from .._sdk import enable_plugin_in_config, read_positive_integer_param
from .client import FirecrawlScrapeParams, run_firecrawl_scrape
from .fetch_provider_shared import FIRECRAWL_WEB_FETCH_PROVIDER_SHARED


def create_firecrawl_web_fetch_provider() -> dict:
    shared = dict(FIRECRAWL_WEB_FETCH_PROVIDER_SHARED)

    def apply_selection_config(config: dict) -> dict:
        return enable_plugin_in_config(config, "firecrawl")

    def create_tool(*, config: dict) -> dict:
        async def execute(args: dict) -> dict:
            url = args["url"] if isinstance(args.get("url"), str) else ""
            extract_mode = "text" if args.get("extractMode") == "text" else "markdown"
            max_chars = read_positive_integer_param(args, "maxChars")
            proxy = args.get("proxy") if args.get("proxy") in ("basic", "stealth", "auto") else None
            store_in_cache = args.get("storeInCache") if isinstance(args.get("storeInCache"), bool) else None
            params = FirecrawlScrapeParams(
                cfg=config,
                url=url,
                extract_mode=extract_mode,
                access="keyless",
                max_chars=max_chars,
                proxy=proxy,
                store_in_cache=store_in_cache,
            )
            return await run_firecrawl_scrape(params)

        return {
            "description": "Fetch a page using Firecrawl.",
            "parameters": {},
            "execute": execute,
        }

    shared["applySelectionConfig"] = apply_selection_config
    shared["createTool"] = create_tool
    return shared
