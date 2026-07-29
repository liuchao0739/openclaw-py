from .._sdk import enable_plugin_in_config
from .fetch_provider_shared import FIRECRAWL_WEB_FETCH_PROVIDER_SHARED


def create_firecrawl_web_fetch_provider() -> dict:
    shared = dict(FIRECRAWL_WEB_FETCH_PROVIDER_SHARED)

    def apply_selection_config(config: dict) -> dict:
        return enable_plugin_in_config(config, "firecrawl")

    shared["applySelectionConfig"] = apply_selection_config
    shared["createTool"] = lambda: None
    return shared
