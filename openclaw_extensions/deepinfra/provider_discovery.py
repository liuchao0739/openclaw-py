from .provider_catalog import build_deepinfra_api_key_catalog, build_static_deepinfra_provider

PROVIDER_ID = "deepinfra"

deepinfra_provider_discovery = {
    "id": PROVIDER_ID,
    "label": "DeepInfra",
    "docsPath": "/providers/deepinfra",
    "auth": [],
    "catalog": {
        "order": "simple",
        "run": build_deepinfra_api_key_catalog,
    },
    "staticCatalog": {
        "order": "simple",
        "run": lambda: {"provider": build_static_deepinfra_provider()},
    },
}

__all__ = ["deepinfra_provider_discovery"]