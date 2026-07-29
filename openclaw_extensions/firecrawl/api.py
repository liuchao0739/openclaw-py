from typing import Optional

from .._sdk import read_string_value
from .client import FirecrawlScrapeParams, run_firecrawl_scrape


class FetchFirecrawlContentParams:
    def __init__(self, *, url: str, extract_mode: str, api_key: str, base_url: str,
                 only_main_content: bool, max_age_ms: int, proxy: str,
                 store_in_cache: bool, timeout_seconds: int, max_chars: Optional[int] = None):
        self.url = url
        self.extract_mode = extract_mode
        self.api_key = api_key
        self.base_url = base_url
        self.only_main_content = only_main_content
        self.max_age_ms = max_age_ms
        self.proxy = proxy
        self.store_in_cache = store_in_cache
        self.timeout_seconds = timeout_seconds
        self.max_chars = max_chars


class FetchFirecrawlContentResult:
    def __init__(self, *, text: str, title: Optional[str] = None, final_url: Optional[str] = None,
                 status: Optional[int] = None, warning: Optional[str] = None):
        self.text = text
        self.title = title
        self.final_url = final_url
        self.status = status
        self.warning = warning


async def fetch_firecrawl_content(params: FetchFirecrawlContentParams) -> FetchFirecrawlContentResult:
    cfg = {
        "plugins": {
            "entries": {
                "firecrawl": {
                    "enabled": True,
                    "config": {
                        "webFetch": {
                            "apiKey": params.api_key,
                            "baseUrl": params.base_url,
                            "onlyMainContent": params.only_main_content,
                            "maxAgeMs": params.max_age_ms,
                            "timeoutSeconds": params.timeout_seconds,
                        },
                    },
                },
            },
        },
    }

    scrape_params = FirecrawlScrapeParams(
        cfg=cfg,
        url=params.url,
        extract_mode=params.extract_mode,
        max_chars=params.max_chars,
        proxy=params.proxy,
        store_in_cache=params.store_in_cache,
        only_main_content=params.only_main_content,
        max_age_ms=params.max_age_ms,
        timeout_seconds=params.timeout_seconds,
    )
    result = await run_firecrawl_scrape(scrape_params)

    return FetchFirecrawlContentResult(
        text=result.get("text", "") if isinstance(result.get("text"), str) else "",
        title=read_string_value(result.get("title")),
        final_url=read_string_value(result.get("finalUrl")),
        status=result.get("status") if isinstance(result.get("status"), int) else None,
        warning=read_string_value(result.get("warning")),
    )
