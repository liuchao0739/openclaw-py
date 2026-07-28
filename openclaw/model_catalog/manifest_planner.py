from __future__ import annotations

from typing import Any, Literal, TypedDict

from openclaw_packages.model_catalog_core.model_catalog_normalize import (
    normalize_model_catalog_provider_rows,
)
from openclaw_packages.model_catalog_core.model_catalog_refs import (
    build_model_catalog_merge_key,
    normalize_model_catalog_provider_id,
)
from openclaw_packages.model_catalog_core.model_catalog_types import (
    ModelCatalog,
    ModelCatalogAlias,
    ModelCatalogDiscovery,
    NormalizedModelCatalogRow,
)
from openclaw_packages.normalization_core import (
    normalize_lowercase_string_or_empty,
    normalize_unique_string_entries,
)


class ManifestModelCatalogPlugin(TypedDict, total=False):
    id: str
    providers: list[str]
    modelCatalog: ModelCatalog


class ManifestModelCatalogRegistry(TypedDict):
    plugins: list[ManifestModelCatalogPlugin]


class ManifestModelCatalogPlanEntry(TypedDict):
    pluginId: str
    provider: str
    discovery: ModelCatalogDiscovery | None
    rows: list[NormalizedModelCatalogRow]


class ManifestModelCatalogConflict(TypedDict):
    mergeKey: str
    ref: str
    provider: str
    modelId: str
    firstPluginId: str
    secondPluginId: str


class ManifestModelCatalogPlan(TypedDict):
    rows: list[NormalizedModelCatalogRow]
    entries: list[ManifestModelCatalogPlanEntry]
    conflicts: list[ManifestModelCatalogConflict]


class ManifestModelCatalogSuppressionEntry(TypedDict):
    pluginId: str
    provider: str
    model: str
    mergeKey: str
    reason: str | None
    when: dict[str, list[str]] | None


class ManifestModelCatalogSuppressionPlan(TypedDict):
    suppressions: list[ManifestModelCatalogSuppressionEntry]


def _build_owned_provider_set(plugin: ManifestModelCatalogPlugin) -> set[str]:
    return set(
        normalize_unique_string_entries(
            [normalize_model_catalog_provider_id(p) for p in (plugin.get("providers") or [])]
        )
    )


def _build_model_catalog_provider_alias_targets(
    plugin: ManifestModelCatalogPlugin,
) -> dict[str, list[str]]:
    owned_providers = _build_owned_provider_set(plugin)
    aliases_by_target_provider: dict[str, list[str]] = {}
    for raw_alias, alias in (plugin.get("modelCatalog") or {}).get("aliases", {}).items():
        alias_provider = normalize_model_catalog_provider_id(raw_alias)
        target_provider = normalize_model_catalog_provider_id(alias.get("provider", ""))
        if not alias_provider or not target_provider or target_provider not in owned_providers:
            continue
        aliases = aliases_by_target_provider.get(target_provider, [])
        aliases.append(alias_provider)
        aliases_by_target_provider[target_provider] = aliases
    return aliases_by_target_provider


def _build_model_catalog_provider_refs(plugin: ManifestModelCatalogPlugin) -> set[str]:
    owned_providers = _build_owned_provider_set(plugin)
    refs = set(owned_providers)
    for raw_alias, alias in (plugin.get("modelCatalog") or {}).get("aliases", {}).items():
        alias_provider = normalize_model_catalog_provider_id(raw_alias)
        target_provider = normalize_model_catalog_provider_id(alias.get("provider", ""))
        if alias_provider and target_provider and target_provider in owned_providers:
            refs.add(alias_provider)
    return refs


def _apply_model_catalog_alias_overrides(
    rows: list[NormalizedModelCatalogRow],
    alias: ModelCatalogAlias | None,
) -> list[NormalizedModelCatalogRow]:
    if not alias:
        return rows
    result: list[NormalizedModelCatalogRow] = []
    for row in rows:
        new_row: NormalizedModelCatalogRow = dict(row)
        if alias.get("api"):
            new_row["api"] = alias["api"]
        if alias.get("baseUrl"):
            new_row["baseUrl"] = alias["baseUrl"]
        result.append(new_row)
    return result


def _plan_manifest_model_catalog_plugin_entries(
    plugin: ManifestModelCatalogPlugin,
    provider_filter: str | None,
) -> list[ManifestModelCatalogPlanEntry]:
    providers = (plugin.get("modelCatalog") or {}).get("providers")
    if not providers:
        return []

    aliases_by_target_provider = _build_model_catalog_provider_alias_targets(plugin)

    entries: list[ManifestModelCatalogPlanEntry] = []
    for provider, provider_catalog in providers.items():
        normalized_provider = normalize_model_catalog_provider_id(provider)
        if not normalized_provider:
            continue
        provider_aliases = aliases_by_target_provider.get(normalized_provider, [])
        if provider_filter:
            if provider_filter in provider_aliases or normalized_provider == provider_filter:
                planned_providers = [provider_filter]
            else:
                continue
        else:
            planned_providers = [normalized_provider]

        for planned_provider in planned_providers:
            rows = normalize_model_catalog_provider_rows(
                provider=planned_provider,
                provider_catalog=provider_catalog,
                source="manifest",
            )
            if not rows:
                continue
            entries.append({
                "pluginId": plugin["id"],
                "provider": planned_provider,
                "discovery": (plugin.get("modelCatalog") or {}).get("discovery", {}).get(normalized_provider),
                "rows": _apply_model_catalog_alias_overrides(
                    rows,
                    (plugin.get("modelCatalog") or {}).get("aliases", {}).get(planned_provider),
                ),
            })
    return entries


def plan_manifest_model_catalog_rows(
    *,
    registry: ManifestModelCatalogRegistry,
    provider_filter: str | None = None,
) -> ManifestModelCatalogPlan:
    normalized_provider_filter = (
        normalize_model_catalog_provider_id(provider_filter) if provider_filter else None
    )
    entries: list[ManifestModelCatalogPlanEntry] = []

    for plugin in registry["plugins"]:
        plugin_entries = _plan_manifest_model_catalog_plugin_entries(
            plugin, normalized_provider_filter
        )
        entries.extend(plugin_entries)

    row_candidates: list[NormalizedModelCatalogRow] = []
    seen_rows: dict[str, tuple[str, NormalizedModelCatalogRow]] = {}
    conflicts: dict[str, ManifestModelCatalogConflict] = {}

    for entry in entries:
        for row in entry["rows"]:
            seen = seen_rows.get(row["mergeKey"])
            if seen is not None:
                if row["mergeKey"] not in conflicts:
                    conflicts[row["mergeKey"]] = {
                        "mergeKey": row["mergeKey"],
                        "ref": seen[1]["ref"],
                        "provider": seen[1]["provider"],
                        "modelId": seen[1]["id"],
                        "firstPluginId": seen[0],
                        "secondPluginId": entry["pluginId"],
                    }
                continue
            seen_rows[row["mergeKey"]] = (entry["pluginId"], row)
            row_candidates.append(row)

    conflicted_merge_keys = set(conflicts.keys())
    rows = [row for row in row_candidates if row["mergeKey"] not in conflicted_merge_keys]

    return {
        "entries": entries,
        "conflicts": list(conflicts.values()),
        "rows": sorted(rows, key=lambda r: (r["provider"], r["id"])),
    }


def plan_manifest_model_catalog_suppressions(
    *,
    registry: ManifestModelCatalogRegistry,
    provider_filter: str | None = None,
    model_filter: str | None = None,
) -> ManifestModelCatalogSuppressionPlan:
    normalized_provider_filter = (
        normalize_model_catalog_provider_id(provider_filter) if provider_filter else None
    )
    normalized_model_filter = (
        normalize_lowercase_string_or_empty(model_filter) if model_filter else None
    )
    suppressions: list[ManifestModelCatalogSuppressionEntry] = []

    for plugin in registry["plugins"]:
        provider_refs = _build_model_catalog_provider_refs(plugin)
        for suppression in (plugin.get("modelCatalog") or {}).get("suppressions", []):
            provider = normalize_model_catalog_provider_id(suppression.get("provider", ""))
            model = normalize_lowercase_string_or_empty(suppression.get("model", ""))
            if not provider or not model:
                continue
            if normalized_provider_filter and provider != normalized_provider_filter:
                continue
            if normalized_model_filter and model != normalized_model_filter:
                continue
            if provider not in provider_refs:
                continue
            entry: ManifestModelCatalogSuppressionEntry = {
                "pluginId": plugin["id"],
                "provider": provider,
                "model": model,
                "mergeKey": build_model_catalog_merge_key(provider, model),
                "reason": suppression.get("reason"),
                "when": suppression.get("when"),
            }
            suppressions.append(entry)

    return {
        "suppressions": sorted(
            suppressions,
            key=lambda s: (s["provider"], s["model"], s["pluginId"]),
        ),
    }


__all__ = [
    "ManifestModelCatalogConflict",
    "ManifestModelCatalogPlan",
    "ManifestModelCatalogPlanEntry",
    "ManifestModelCatalogPlugin",
    "ManifestModelCatalogRegistry",
    "ManifestModelCatalogSuppressionEntry",
    "ManifestModelCatalogSuppressionPlan",
    "plan_manifest_model_catalog_rows",
    "plan_manifest_model_catalog_suppressions",
]
