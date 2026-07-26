"""Firecrawl API module exposes the plugin public contract."""

from __future__ import annotations

from typing import Literal, TypedDict

from openclaw.packages.normalization_core import read_string_value
from openclaw_extensions.firecrawl.src.firecrawl_client import run_firecrawl_scrape


class FetchFirecrawlContentParams(TypedDict, total=False):
    url: str
    extractMode: Literal["markdown", "text"]
    apiKey: str
    baseUrl: str
    onlyMainContent: bool
    maxAgeMs: int
    proxy: Literal["auto", "basic", "stealth"]
    storeInCache: bool
    timeoutSeconds: int
    maxChars: int


class FetchFirecrawlContentResult(TypedDict, total=False):
    text: str
    title: str | None
    finalUrl: str | None
    status: int | None
    warning: str | None


async def fetch_firecrawl_content(params: FetchFirecrawlContentParams) -> FetchFirecrawlContentResult:
    cfg = {
        "plugins": {
            "entries": {
                "firecrawl": {
                    "enabled": True,
                    "config": {
                        "webFetch": {
                            "apiKey": params["apiKey"],
                            "baseUrl": params["baseUrl"],
                            "onlyMainContent": params["onlyMainContent"],
                            "maxAgeMs": params["maxAgeMs"],
                            "timeoutSeconds": params["timeoutSeconds"],
                        }
                    },
                }
            }
        }
    }
    result = await run_firecrawl_scrape(
        {
            "cfg": cfg,
            "url": params["url"],
            "extractMode": params["extractMode"],
            "maxChars": params.get("maxChars"),
            "proxy": params.get("proxy"),
            "storeInCache": params.get("storeInCache"),
            "onlyMainContent": params.get("onlyMainContent"),
            "maxAgeMs": params.get("maxAgeMs"),
            "timeoutSeconds": params.get("timeoutSeconds"),
        }
    )
    status = result.get("status")
    return {
        "text": result.get("text") if isinstance(result.get("text"), str) else "",
        "title": read_string_value(result.get("title")),
        "finalUrl": read_string_value(result.get("finalUrl")),
        "status": status if isinstance(status, int) else None,
        "warning": read_string_value(result.get("warning")),
    }
