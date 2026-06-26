"""Model-catalog authority merging chooses the strongest source for duplicate
provider/model rows.

Mirrors src/model-catalog/authority.ts.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

MODEL_CATALOG_SOURCE_AUTHORITY: dict[str, int] = {
    "config": 0,
    "manifest": 1,
    "cache": 2,
    "runtime-refresh": 2,
    "provider-index": 3,
}


@dataclass
class NormalizedModelCatalogRow:
    """A normalized model catalog row."""

    merge_key: str
    provider: str
    id: str
    source: str = "config"


def _compare_source_authority(left: str, right: str) -> int:
    return MODEL_CATALOG_SOURCE_AUTHORITY.get(left, 99) - MODEL_CATALOG_SOURCE_AUTHORITY.get(right, 99)


def merge_model_catalog_rows_by_authority(
    rows: Iterable[NormalizedModelCatalogRow],
) -> list[NormalizedModelCatalogRow]:
    """Merge duplicate catalog rows by source authority.

    Lower numeric authority wins: explicit config beats manifest/runtime discovery,
    while provider-index preview data is the weakest source.
    """
    by_merge_key: dict[str, NormalizedModelCatalogRow] = {}
    for row in rows:
        existing = by_merge_key.get(row.merge_key)
        if existing is None or _compare_source_authority(row.source, existing.source) < 0:
            by_merge_key[row.merge_key] = row
    return sorted(
        by_merge_key.values(),
        key=lambda r: (r.provider, r.id),
    )
