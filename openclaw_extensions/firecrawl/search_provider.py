from .._sdk import read_positive_integer_param
from .client import FirecrawlSearchParams, run_firecrawl_search
from .web_search_shared import build_firecrawl_web_search_provider_base

_firecrawl_client_module = None


def _load_firecrawl_client_module():
    global _firecrawl_client_module
    if _firecrawl_client_module is None:
        from . import client as _client
        _firecrawl_client_module = _client
    return _firecrawl_client_module


GENERIC_FIRECRAWL_SEARCH_SCHEMA = {
    "type": "object",
    "properties": {
        "query": {"type": "string", "description": "Search query string."},
        "count": {
            "type": "integer",
            "description": "Number of results to return (1-10).",
            "minimum": 1,
            "maximum": 10,
        },
    },
    "additionalProperties": False,
}


def create_firecrawl_web_search_provider() -> dict:
    base = build_firecrawl_web_search_provider_base()

    def create_tool(ctx: dict) -> dict:
        async def execute(args: dict) -> dict:
            module = _load_firecrawl_client_module()
            params = FirecrawlSearchParams(
                cfg=ctx["config"],
                query=args["query"] if isinstance(args.get("query"), str) else "",
                count=read_positive_integer_param(
                    args, "count", message="count must be an integer from 1 to 10", max=10
                ),
            )
            return await module.run_firecrawl_search(params)

        return {
            "description": "Search the web using Firecrawl. Returns structured results with snippets from Firecrawl Search. Use firecrawl_search for Firecrawl-specific knobs like sources or categories.",
            "parameters": GENERIC_FIRECRAWL_SEARCH_SCHEMA,
            "execute": execute,
        }

    base["createTool"] = create_tool
    return base
