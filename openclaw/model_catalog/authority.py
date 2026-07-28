from __future__ import annotations

from typing import Iterable

from openclaw_packages.model_catalog_core.model_catalog_types import (
    ModelCatalogSource,
    NormalizedModelCatalogRow,
)

MODEL_CATALOG_SOURCE_AUTHORITY: dict[ModelCatalogSource, int] = {
    "config": 0,
    "manifest": 1,
    "cache": 2,
    "runtime-refresh": 2,
    "provider-index": 3,
}


def _compare_source_authority(left: ModelCatalogSource, right: ModelCatalogSource) -> int:
    return MODEL_CATALOG_SOURCE_AUTHORITY.get(left, 99) - MODEL_CATALOG_SOURCE_AUTHORITY.get(right, 99)


def merge_model_catalog_rows_by_authority(
    rows: Iterable[NormalizedModelCatalogRow],
) -> list[NormalizedModelCatalogRow]:
    by_merge_key: dict[str, NormalizedModelCatalogRow] = {}
    for row in rows:
        existing = by_merge_key.get(row["mergeKey"])
        if existing is None or _compare_source_authority(row["source"], existing["source"]) < 0:
            by_merge_key[row["mergeKey"]] = row
    return sorted(
        by_merge_key.values(),
        key=lambda r: (r["provider"], r["id"]),
    )


__all__ = [
    "MODEL_CATALOG_SOURCE_AUTHORITY",
    "merge_model_catalog_rows_by_authority",
]
