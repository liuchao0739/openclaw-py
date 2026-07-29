from .src.web_search_provider_shared import create_codex_web_search_provider_base


def create_codex_web_search_provider():
    base = create_codex_web_search_provider_base()
    base["createTool"] = lambda: None
    return base
