"""Tests for model-catalog authority module."""

from openclaw.model_catalog.authority import (
    MODEL_CATALOG_SOURCE_AUTHORITY,
    merge_model_catalog_rows_by_authority,
    NormalizedModelCatalogRow,
)


def test_config_beats_manifest():
    rows = [
        NormalizedModelCatalogRow(merge_key="openai/gpt-4", provider="openai", id="gpt-4", source="manifest"),
        NormalizedModelCatalogRow(merge_key="openai/gpt-4", provider="openai", id="gpt-4", source="config"),
    ]
    result = merge_model_catalog_rows_by_authority(rows)
    assert len(result) == 1
    assert result[0].source == "config"

def test_manifest_beats_cache():
    rows = [
        NormalizedModelCatalogRow(merge_key="x", provider="p", id="m", source="cache"),
        NormalizedModelCatalogRow(merge_key="x", provider="p", id="m", source="manifest"),
    ]
    result = merge_model_catalog_rows_by_authority(rows)
    assert result[0].source == "manifest"

def test_provider_index_is_weakest():
    rows = [
        NormalizedModelCatalogRow(merge_key="x", provider="p", id="m", source="provider-index"),
        NormalizedModelCatalogRow(merge_key="x", provider="p", id="m", source="runtime-refresh"),
    ]
    result = merge_model_catalog_rows_by_authority(rows)
    assert result[0].source == "runtime-refresh"

def test_no_duplicates():
    rows = [
        NormalizedModelCatalogRow(merge_key="a", provider="a", id="1", source="config"),
        NormalizedModelCatalogRow(merge_key="b", provider="b", id="2", source="config"),
    ]
    result = merge_model_catalog_rows_by_authority(rows)
    assert len(result) == 2

def test_sorted_by_provider_then_id():
    rows = [
        NormalizedModelCatalogRow(merge_key="b", provider="beta", id="z", source="config"),
        NormalizedModelCatalogRow(merge_key="a", provider="alpha", id="y", source="config"),
        NormalizedModelCatalogRow(merge_key="c", provider="alpha", id="x", source="config"),
    ]
    result = merge_model_catalog_rows_by_authority(rows)
    assert result[0].provider == "alpha"
    assert result[0].id == "x"
    assert result[1].provider == "alpha"
    assert result[1].id == "y"
    assert result[2].provider == "beta"

def test_empty():
    assert merge_model_catalog_rows_by_authority([]) == []

def test_first_row_wins_on_tie():
    rows = [
        NormalizedModelCatalogRow(merge_key="x", provider="p", id="m", source="config"),
        NormalizedModelCatalogRow(merge_key="x", provider="p", id="m", source="config"),
    ]
    result = merge_model_catalog_rows_by_authority(rows)
    assert len(result) == 1
    # First row should win on tie (existing is kept when authority is equal)
    assert result[0] is rows[0]
