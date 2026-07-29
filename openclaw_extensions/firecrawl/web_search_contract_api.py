from .web_search_shared import build_firecrawl_web_search_provider_base


def create_firecrawl_web_search_provider() -> dict:
    base = build_firecrawl_web_search_provider_base()
    base["createTool"] = lambda: None
    return base
