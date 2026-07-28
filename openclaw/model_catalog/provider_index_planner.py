from __future__ import annotations

from typing import Any, TypedDict

from openclaw_packages.model_catalog_core.model_catalog_normalize import (
    normalize_model_catalog_provider_rows,
)
from openclaw_packages.model_catalog_core.model_catalog_refs import (
    normalize_model_catalog_provider_id,
)
from openclaw_packages.model_catalog_core.model_catalog_types import (
    ModelCatalogProvider,
    NormalizedModelCatalogRow,
)

from .provider_index.types import OpenClawProviderIndex


class ProviderIndexModelCatalogPlanEntry(TypedDict):
    provider: str
    pluginId: str
    rows: list[NormalizedModelCatalogRow]


class ProviderIndexModelCatalogPlan(TypedDict):
    rows: list[NormalizedModelCatalogRow]
    entries: list[ProviderIndexModelCatalogPlanEntry]


def _with_preview_status_defaults(provider_catalog: ModelCatalogProvider) -> ModelCatalogProvider:
    models = [
        {**model, "status": model.get("status", "preview")}
        for model in provider_catalog.get("models", [])
    ]
    result: ModelCatalogProvider = dict(provider_catalog)
    result["models"] = models
    return result


def plan_provider_index_model_catalog_rows(
    *,
    index: OpenClawProviderIndex,
    provider_filter: str | None = None,
) -> ProviderIndexModelCatalogPlan:
    normalized_provider_filter = (
        normalize_model_catalog_provider_id(provider_filter) if provider_filter else None
    )
    entries: list[ProviderIndexModelCatalogPlanEntry] = []

    for provider_id, provider in index["providers"].items():
        normalized_provider = normalize_model_catalog_provider_id(provider_id)
        if (
            not normalized_provider
            or (normalized_provider_filter and normalized_provider != normalized_provider_filter)
            or not provider.get("previewCatalog")
        ):
            continue
        preview_catalog = provider["previewCatalog"]
        rows = normalize_model_catalog_provider_rows(
            provider=normalized_provider,
            provider_catalog=_with_preview_status_defaults(preview_catalog),
            source="provider-index",
        )
        if not rows:
            continue
        entries.append({
            "provider": normalized_provider,
            "pluginId": provider["plugin"]["id"],
            "rows": rows,
        })

    all_rows = [row for entry in entries for row in entry["rows"]]
    return {
        "entries": entries,
        "rows": sorted(all_rows, key=lambda r: (r["provider"], r["id"])),
    }


__all__ = [
    "ProviderIndexModelCatalogPlan",
    "ProviderIndexModelCatalogPlanEntry",
    "plan_provider_index_model_catalog_rows",
]
