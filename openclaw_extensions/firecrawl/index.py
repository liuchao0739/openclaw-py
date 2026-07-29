from .fetch_provider import create_firecrawl_web_fetch_provider
from .scrape_tool import create_firecrawl_scrape_tool
from .search_provider import create_firecrawl_web_search_provider
from .search_tool import create_firecrawl_search_tool


def define_plugin_entry(*, id: str, name: str, description: str, register):
    return {
        "id": id,
        "name": name,
        "description": description,
        "register": register,
    }


def _register(api):
    api["registerWebFetchProvider"](create_firecrawl_web_fetch_provider())
    api["registerWebSearchProvider"](create_firecrawl_web_search_provider())
    api["registerTool"](create_firecrawl_search_tool(api))
    api["registerTool"](create_firecrawl_scrape_tool(api))


default = define_plugin_entry(
    id="firecrawl",
    name="Firecrawl Plugin",
    description="Bundled Firecrawl search and scrape plugin",
    register=_register,
)
