from typing import Any, Optional

from .provider_catalog import build_deepseek_provider


def _run_static_discovery() -> dict:
    return {"provider": build_deepseek_provider()}


class ProviderDiscovery:
    id: str = "deepseek"
    label: str = "DeepSeek"
    docs_path: str = "/providers/deepseek"
    auth: list = []
    static_catalog: dict

    def __init__(self) -> None:
        self.static_catalog = {
            "order": "simple",
            "run": _run_static_discovery,
        }


deepseek_provider_discovery = ProviderDiscovery()


def get_provider_discovery() -> ProviderDiscovery:
    return deepseek_provider_discovery
