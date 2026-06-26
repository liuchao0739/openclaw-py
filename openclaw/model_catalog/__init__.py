"""Model catalog package — authority merging."""

from .authority import (
    MODEL_CATALOG_SOURCE_AUTHORITY,
    merge_model_catalog_rows_by_authority,
)

__all__ = [
    "MODEL_CATALOG_SOURCE_AUTHORITY",
    "merge_model_catalog_rows_by_authority",
]
