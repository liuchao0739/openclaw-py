"""Normalize raw provider model catalogs into stable rows for lookup and merging.

Mirrors packages/model-catalog-core/src/model-catalog-normalize.ts.
"""

from __future__ import annotations

from typing import Any

from openclaw_packages.normalization_core import (
    as_finite_number,
    is_record,
    normalize_optional_string,
    normalize_optional_trimmed_string_list,
    normalize_trimmed_string_list,
)

from .model_catalog_refs import (
    build_model_catalog_merge_key,
    build_model_catalog_ref,
    normalize_model_catalog_provider_id,
)
from .model_catalog_types import (
    MODEL_CATALOG_APIS,
    ModelCatalog,
    ModelCatalogAlias,
    ModelCatalogApi,
    ModelCatalogCompatConfig,
    ModelCatalogCost,
    ModelCatalogDiscovery,
    ModelCatalogInput,
    ModelCatalogModel,
    ModelCatalogProvider,
    ModelCatalogSource,
    ModelCatalogStatus,
    ModelCatalogSuppression,
    ModelCatalogTieredCost,
    NormalizedModelCatalogRow,
    is_model_catalog_thinking_format,
)

_MODEL_CATALOG_INPUTS = frozenset({"text", "image", "document"})
_MODEL_CATALOG_DISCOVERY_MODES = frozenset({"static", "refreshable", "runtime"})
_MODEL_CATALOG_STATUSES = frozenset({"available", "preview", "deprecated", "disabled"})
_MODEL_CATALOG_API_SET = frozenset(MODEL_CATALOG_APIS)
_DEFAULT_MODEL_INPUT: list[ModelCatalogInput] = ["text"]
_DEFAULT_MODEL_STATUS: ModelCatalogStatus = "available"


def _is_blocked_object_key(key: str) -> bool:
    return key in ("__proto__", "prototype", "constructor")


def _normalize_safe_record_key(value: object) -> str:
    key = normalize_optional_string(value) or ""
    return key if key and not _is_blocked_object_key(key) else ""


def _normalize_owned_provider_set(providers: set[str] | frozenset[str]) -> set[str]:
    normalized: set[str] = set()
    for provider in providers:
        provider_id = normalize_model_catalog_provider_id(provider)
        if provider_id:
            normalized.add(provider_id)
    return normalized


def _normalize_string_map(value: object) -> dict[str, str] | None:
    if not is_record(value):
        return None
    normalized: dict[str, str] = {}
    for raw_key, raw_value in value.items():
        key = _normalize_safe_record_key(raw_key)
        map_value = normalize_optional_string(raw_value) or ""
        if key and map_value:
            normalized[key] = map_value
    return normalized or None


def _merge_string_maps(
    base: dict[str, str] | None,
    override: dict[str, str] | None,
) -> dict[str, str] | None:
    if not base and not override:
        return None
    merged: dict[str, str] = {}
    if base:
        merged.update(base)
    if override:
        merged.update(override)
    return merged or None


def _normalize_model_catalog_api(value: object) -> ModelCatalogApi | None:
    api = normalize_optional_string(value) or ""
    return api if api in _MODEL_CATALOG_API_SET else None


def _normalize_model_catalog_inputs(value: object) -> list[ModelCatalogInput] | None:
    inputs = [
        entry
        for entry in normalize_trimmed_string_list(value)
        if entry in _MODEL_CATALOG_INPUTS
    ]
    return inputs or None


def _normalize_non_negative_number(value: object) -> float | None:
    num = as_finite_number(value)
    return num if num is not None and num >= 0 else None


def _normalize_finite_number(value: object) -> float | None:
    return as_finite_number(value)


def _normalize_string_or_number(value: object) -> str | float | None:
    return normalize_optional_string(value) or _normalize_finite_number(value)


def _normalize_positive_number(value: object) -> float | None:
    num = as_finite_number(value)
    return num if num is not None and num > 0 else None


def _normalize_positive_integer(value: object) -> int | None:
    if isinstance(value, int) and not isinstance(value, bool) and value > 0:
        return value
    return None


def _normalize_model_catalog_tiered_cost(value: object) -> list[ModelCatalogTieredCost] | None:
    if not isinstance(value, list):
        return None
    normalized: list[ModelCatalogTieredCost] = []
    for entry in value:
        if not is_record(entry) or not isinstance(entry.get("range"), list):
            continue
        entry_range = entry["range"]
        input_cost = _normalize_non_negative_number(entry.get("input"))
        output_cost = _normalize_non_negative_number(entry.get("output"))
        cache_read = _normalize_non_negative_number(entry.get("cacheRead"))
        cache_write = _normalize_non_negative_number(entry.get("cacheWrite"))
        if (
            input_cost is None
            or output_cost is None
            or cache_read is None
            or cache_write is None
            or len(entry_range) < 1
            or len(entry_range) > 2
        ):
            continue
        range_values = [_normalize_non_negative_number(range_value) for range_value in entry_range]
        if any(range_value is None for range_value in range_values):
            continue
        assert all(range_value is not None for range_value in range_values)
        typed_range: tuple[float, ...] = (
            (range_values[0],)
            if len(range_values) == 1
            else (range_values[0], range_values[1])
        )
        normalized.append(
            {
                "input": input_cost,
                "output": output_cost,
                "cacheRead": cache_read,
                "cacheWrite": cache_write,
                "range": typed_range,
            },
        )
    return normalized or None


def _normalize_model_catalog_cost(value: object) -> ModelCatalogCost | None:
    if not is_record(value):
        return None
    cost: ModelCatalogCost = {}
    input_cost = _normalize_non_negative_number(value.get("input"))
    output_cost = _normalize_non_negative_number(value.get("output"))
    cache_read = _normalize_non_negative_number(value.get("cacheRead"))
    cache_write = _normalize_non_negative_number(value.get("cacheWrite"))
    tiered_pricing = _normalize_model_catalog_tiered_cost(value.get("tieredPricing"))
    if input_cost is not None:
        cost["input"] = input_cost
    if output_cost is not None:
        cost["output"] = output_cost
    if cache_read is not None:
        cost["cacheRead"] = cache_read
    if cache_write is not None:
        cost["cacheWrite"] = cache_write
    if tiered_pricing:
        cost["tieredPricing"] = tiered_pricing
    return cost or None


def _normalize_open_router_price(value: object) -> dict[str, str | float] | None:
    if not is_record(value):
        return None
    max_price: dict[str, str | float] = {}
    for field in ("prompt", "completion", "image", "audio", "request"):
        normalized = _normalize_string_or_number(value.get(field))
        if normalized is not None:
            max_price[field] = normalized
    return max_price or None


def _normalize_open_router_percentile_cutoffs(value: object) -> dict[str, float] | None:
    if not is_record(value):
        return None
    normalized: dict[str, float] = {}
    for field in ("p50", "p75", "p90", "p99"):
        cutoff = _normalize_finite_number(value.get(field))
        if cutoff is not None:
            normalized[field] = cutoff
    return normalized or None


def _normalize_open_router_metric_preference(
    value: object,
) -> float | dict[str, float] | None:
    return _normalize_finite_number(value) or _normalize_open_router_percentile_cutoffs(value)


def _normalize_open_router_sort(value: object) -> str | dict[str, str | None] | None:
    sort = normalize_optional_string(value)
    if sort:
        return sort
    if not is_record(value):
        return None
    by = normalize_optional_string(value.get("by"))
    normalized: dict[str, str | None] = {}
    if by:
        normalized["by"] = by
    if "partition" in value:
        partition_raw = value["partition"]
        if partition_raw is None:
            normalized["partition"] = None
        else:
            partition = normalize_optional_string(partition_raw)
            if partition is not None:
                normalized["partition"] = partition
    return normalized or None


def _normalize_open_router_routing(value: object) -> dict[str, Any] | None:
    if not is_record(value):
        return None
    routing: dict[str, Any] = {}
    if isinstance(value.get("allow_fallbacks"), bool):
        routing["allow_fallbacks"] = value["allow_fallbacks"]
    if isinstance(value.get("require_parameters"), bool):
        routing["require_parameters"] = value["require_parameters"]
    data_collection = value.get("data_collection")
    if data_collection in ("deny", "allow"):
        routing["data_collection"] = data_collection
    if isinstance(value.get("zdr"), bool):
        routing["zdr"] = value["zdr"]
    if isinstance(value.get("enforce_distillable_text"), bool):
        routing["enforce_distillable_text"] = value["enforce_distillable_text"]
    for field in ("order", "only", "ignore", "quantizations"):
        normalized_list = normalize_optional_trimmed_string_list(value.get(field))
        if normalized_list:
            routing[field] = normalized_list
    sort = _normalize_open_router_sort(value.get("sort"))
    if sort is not None:
        routing["sort"] = sort
    max_price = _normalize_open_router_price(value.get("max_price"))
    if max_price:
        routing["max_price"] = max_price
    for field in ("preferred_min_throughput", "preferred_max_latency"):
        metric = _normalize_open_router_metric_preference(value.get(field))
        if metric is not None:
            routing[field] = metric
    return routing or None


def _normalize_vercel_gateway_routing(value: object) -> dict[str, list[str]] | None:
    if not is_record(value):
        return None
    routing: dict[str, list[str]] = {}
    for field in ("only", "order"):
        normalized_list = normalize_optional_trimmed_string_list(value.get(field))
        if normalized_list:
            routing[field] = normalized_list
    return routing or None


def _normalize_model_catalog_compat(value: object) -> ModelCatalogCompatConfig | None:
    if not is_record(value):
        return None
    compat: dict[str, Any] = {}
    boolean_fields = (
        "supportsStore",
        "supportsPromptCacheKey",
        "supportsDeveloperRole",
        "supportsReasoningEffort",
        "supportsUsageInStreaming",
        "supportsTools",
        "supportsStrictMode",
        "requiresStringContent",
        "strictMessageKeys",
        "requiresToolResultName",
        "requiresAssistantAfterToolResult",
        "requiresThinkingAsText",
        "zaiToolStream",
        "sendSessionAffinityHeaders",
        "sendSessionIdHeader",
        "supportsEagerToolInputStreaming",
        "supportsLongCacheRetention",
        "nativeWebSearchTool",
        "requiresMistralToolIds",
        "requiresOpenAiAnthropicToolPayload",
    )
    for field in boolean_fields:
        if isinstance(value.get(field), bool):
            compat[field] = value[field]
    for field in ("toolSchemaProfile", "toolCallArgumentsEncoding"):
        normalized = normalize_optional_string(value.get(field)) or ""
        if normalized:
            compat[field] = normalized
    for field in (
        "visibleReasoningDetailTypes",
        "supportedReasoningEfforts",
        "unsupportedToolSchemaKeywords",
    ):
        normalized = normalize_trimmed_string_list(value.get(field))
        if normalized:
            compat[field] = normalized
    reasoning_effort_map_raw = value.get("reasoningEffortMap")
    if is_record(reasoning_effort_map_raw):
        reasoning_effort_map = {
            key.strip(): mapped.strip()
            for key, mapped in reasoning_effort_map_raw.items()
            if isinstance(mapped, str)
            and key.strip()
            and mapped.strip()
        }
        if reasoning_effort_map:
            compat["reasoningEffortMap"] = reasoning_effort_map
    max_tokens_field = normalize_optional_string(value.get("maxTokensField")) or ""
    if max_tokens_field in ("max_completion_tokens", "max_tokens"):
        compat["maxTokensField"] = max_tokens_field
    thinking_format = normalize_optional_string(value.get("thinkingFormat")) or ""
    if is_model_catalog_thinking_format(thinking_format):
        compat["thinkingFormat"] = thinking_format
    if value.get("cacheControlFormat") == "anthropic":
        compat["cacheControlFormat"] = "anthropic"
    open_router_routing = _normalize_open_router_routing(value.get("openRouterRouting"))
    if open_router_routing:
        compat["openRouterRouting"] = open_router_routing
    vercel_gateway_routing = _normalize_vercel_gateway_routing(
        value.get("vercelGatewayRouting"),
    )
    if vercel_gateway_routing:
        compat["vercelGatewayRouting"] = vercel_gateway_routing
    return compat or None


def _normalize_model_catalog_status(value: object) -> ModelCatalogStatus | None:
    status = normalize_optional_string(value) or ""
    return status if status in _MODEL_CATALOG_STATUSES else None


def _normalize_model_catalog_image_token_mode(
    value: object,
) -> str | None:
    token_mode = normalize_optional_string(value) or ""
    return token_mode if token_mode in ("tile", "detail", "provider") else None


def _normalize_model_catalog_media_input(value: object) -> dict[str, Any] | None:
    if not is_record(value) or not is_record(value.get("image")):
        return None
    image = value["image"]
    max_bytes = _normalize_positive_integer(image.get("maxBytes"))
    max_pixels = _normalize_positive_integer(image.get("maxPixels"))
    max_side_px = _normalize_positive_integer(image.get("maxSidePx"))
    preferred_side_px = _normalize_positive_integer(image.get("preferredSidePx"))
    token_mode = _normalize_model_catalog_image_token_mode(image.get("tokenMode"))
    normalized_image: dict[str, Any] = {}
    if max_bytes is not None:
        normalized_image["maxBytes"] = max_bytes
    if max_pixels is not None:
        normalized_image["maxPixels"] = max_pixels
    if max_side_px is not None:
        normalized_image["maxSidePx"] = max_side_px
    if preferred_side_px is not None:
        normalized_image["preferredSidePx"] = preferred_side_px
    if token_mode:
        normalized_image["tokenMode"] = token_mode
    return {"image": normalized_image} if normalized_image else None


def _normalize_model_catalog_model(value: object) -> ModelCatalogModel | None:
    if not is_record(value):
        return None
    model_id = normalize_optional_string(value.get("id")) or ""
    if not model_id:
        return None
    model: ModelCatalogModel = {"id": model_id}
    name = normalize_optional_string(value.get("name")) or ""
    api = _normalize_model_catalog_api(value.get("api"))
    base_url = normalize_optional_string(value.get("baseUrl")) or ""
    headers = _normalize_string_map(value.get("headers"))
    input_modes = _normalize_model_catalog_inputs(value.get("input"))
    reasoning = value.get("reasoning") if isinstance(value.get("reasoning"), bool) else None
    context_window = _normalize_positive_number(value.get("contextWindow"))
    context_tokens = _normalize_positive_integer(value.get("contextTokens"))
    max_tokens = _normalize_positive_number(value.get("maxTokens"))
    cost = _normalize_model_catalog_cost(value.get("cost"))
    compat = _normalize_model_catalog_compat(value.get("compat"))
    media_input = _normalize_model_catalog_media_input(value.get("mediaInput"))
    status = _normalize_model_catalog_status(value.get("status"))
    status_reason = normalize_optional_string(value.get("statusReason")) or ""
    replaces = normalize_trimmed_string_list(value.get("replaces"))
    replaced_by = normalize_optional_string(value.get("replacedBy")) or ""
    tags = normalize_trimmed_string_list(value.get("tags"))
    if name:
        model["name"] = name
    if api:
        model["api"] = api
    if base_url:
        model["baseUrl"] = base_url
    if headers:
        model["headers"] = headers
    if input_modes:
        model["input"] = input_modes
    if reasoning is not None:
        model["reasoning"] = reasoning
    if context_window is not None:
        model["contextWindow"] = context_window
    if context_tokens is not None:
        model["contextTokens"] = context_tokens
    if max_tokens is not None:
        model["maxTokens"] = max_tokens
    if cost:
        model["cost"] = cost
    if compat:
        model["compat"] = compat
    if media_input:
        model["mediaInput"] = media_input
    if status:
        model["status"] = status
    if status_reason:
        model["statusReason"] = status_reason
    if replaces:
        model["replaces"] = replaces
    if replaced_by:
        model["replacedBy"] = replaced_by
    if tags:
        model["tags"] = tags
    return model


def _normalize_model_catalog_provider(value: object) -> ModelCatalogProvider | None:
    if not is_record(value):
        return None
    models_raw = value.get("models")
    models = [
        model
        for entry in (models_raw if isinstance(models_raw, list) else [])
        if (model := _normalize_model_catalog_model(entry))
    ]
    if not models:
        return None
    provider: ModelCatalogProvider = {"models": models}
    base_url = normalize_optional_string(value.get("baseUrl")) or ""
    api = _normalize_model_catalog_api(value.get("api"))
    headers = _normalize_string_map(value.get("headers"))
    if base_url:
        provider["baseUrl"] = base_url
    if api:
        provider["api"] = api
    if headers:
        provider["headers"] = headers
    return provider


def _normalize_model_catalog_providers(
    value: object,
    owned_providers: set[str],
) -> dict[str, ModelCatalogProvider] | None:
    if not is_record(value):
        return None
    providers: dict[str, ModelCatalogProvider] = {}
    for raw_provider_id, raw_provider in value.items():
        provider_id = normalize_model_catalog_provider_id(str(raw_provider_id))
        if not provider_id or provider_id not in owned_providers:
            continue
        provider = _normalize_model_catalog_provider(raw_provider)
        if provider:
            providers[provider_id] = provider
    return providers or None


def _normalize_model_catalog_aliases(
    value: object,
    owned_providers: set[str],
) -> dict[str, ModelCatalogAlias] | None:
    if not is_record(value):
        return None
    aliases: dict[str, ModelCatalogAlias] = {}
    for raw_alias, raw_target in value.items():
        alias = normalize_model_catalog_provider_id(str(raw_alias))
        if not alias or not is_record(raw_target):
            continue
        provider = normalize_model_catalog_provider_id(
            normalize_optional_string(raw_target.get("provider")) or "",
        )
        if not provider or provider not in owned_providers:
            continue
        api = _normalize_model_catalog_api(raw_target.get("api"))
        base_url = normalize_optional_string(raw_target.get("baseUrl")) or ""
        alias_entry: ModelCatalogAlias = {"provider": provider}
        if api:
            alias_entry["api"] = api
        if base_url:
            alias_entry["baseUrl"] = base_url
        aliases[alias] = alias_entry
    return aliases or None


def _normalize_model_catalog_suppressions(value: object) -> list[ModelCatalogSuppression] | None:
    if not isinstance(value, list):
        return None
    suppressions: list[ModelCatalogSuppression] = []
    for entry in value:
        if not is_record(entry):
            continue
        provider = normalize_model_catalog_provider_id(
            normalize_optional_string(entry.get("provider")) or "",
        )
        model = normalize_optional_string(entry.get("model")) or ""
        if not provider or not model:
            continue
        reason = normalize_optional_string(entry.get("reason")) or ""
        raw_when = entry.get("when")
        raw_when = raw_when if is_record(raw_when) else None
        base_url_hosts = [
            host.lower()
            for host in normalize_trimmed_string_list(
                raw_when.get("baseUrlHosts") if raw_when else None,
            )
        ]
        provider_config_api_in = [
            api.lower()
            for api in normalize_trimmed_string_list(
                raw_when.get("providerConfigApiIn") if raw_when else None,
            )
        ]
        when: dict[str, list[str]] = {}
        if base_url_hosts:
            when["baseUrlHosts"] = base_url_hosts
        if provider_config_api_in:
            when["providerConfigApiIn"] = provider_config_api_in
        suppression: ModelCatalogSuppression = {"provider": provider, "model": model}
        if reason:
            suppression["reason"] = reason
        if when:
            suppression["when"] = when
        suppressions.append(suppression)
    return suppressions or None


def _normalize_model_catalog_discovery(
    value: object,
    owned_providers: set[str],
) -> dict[str, ModelCatalogDiscovery] | None:
    if not is_record(value):
        return None
    discovery: dict[str, ModelCatalogDiscovery] = {}
    for raw_provider_id, raw_mode in value.items():
        provider_id = normalize_model_catalog_provider_id(str(raw_provider_id))
        mode = normalize_optional_string(raw_mode) or ""
        if provider_id and provider_id in owned_providers and mode in _MODEL_CATALOG_DISCOVERY_MODES:
            discovery[provider_id] = mode  # type: ignore[assignment]
    return discovery or None


def normalize_model_catalog(
    value: object,
    *,
    owned_providers: set[str] | frozenset[str],
) -> ModelCatalog | None:
    if not is_record(value):
        return None
    owned = _normalize_owned_provider_set(owned_providers)
    providers = _normalize_model_catalog_providers(value.get("providers"), owned)
    aliases = _normalize_model_catalog_aliases(value.get("aliases"), owned)
    suppressions = _normalize_model_catalog_suppressions(value.get("suppressions"))
    discovery = _normalize_model_catalog_discovery(value.get("discovery"), owned)
    runtime_augment = value.get("runtimeAugment") is True
    catalog: ModelCatalog = {}
    if providers:
        catalog["providers"] = providers
    if aliases:
        catalog["aliases"] = aliases
    if suppressions:
        catalog["suppressions"] = suppressions
    if discovery:
        catalog["discovery"] = discovery
    if runtime_augment:
        catalog["runtimeAugment"] = True
    return catalog or None


def normalize_model_catalog_provider_rows(
    *,
    provider: str,
    provider_catalog: ModelCatalogProvider,
    source: ModelCatalogSource,
) -> list[NormalizedModelCatalogRow]:
    normalized_provider = normalize_model_catalog_provider_id(provider)
    models = provider_catalog.get("models")
    if not normalized_provider or not isinstance(models, list):
        return []
    provider_api = _normalize_model_catalog_api(provider_catalog.get("api"))
    provider_base_url = normalize_optional_string(provider_catalog.get("baseUrl")) or ""
    provider_headers = _normalize_string_map(provider_catalog.get("headers"))
    rows: list[NormalizedModelCatalogRow] = []
    for model in models:
        model_id = normalize_optional_string(model.get("id")) or ""
        if not model_id:
            continue
        api = _normalize_model_catalog_api(model.get("api")) or provider_api
        base_url = normalize_optional_string(model.get("baseUrl")) or provider_base_url
        headers = _merge_string_maps(provider_headers, _normalize_string_map(model.get("headers")))
        context_window = _normalize_positive_number(model.get("contextWindow"))
        context_tokens = _normalize_positive_integer(model.get("contextTokens"))
        max_tokens = _normalize_positive_number(model.get("maxTokens"))
        cost = _normalize_model_catalog_cost(model.get("cost"))
        compat = _normalize_model_catalog_compat(model.get("compat"))
        media_input = _normalize_model_catalog_media_input(model.get("mediaInput"))
        status_reason = normalize_optional_string(model.get("statusReason")) or ""
        replaced_by = normalize_optional_string(model.get("replacedBy")) or ""
        replaces = normalize_optional_trimmed_string_list(model.get("replaces"))
        tags = normalize_optional_trimmed_string_list(model.get("tags"))
        row: NormalizedModelCatalogRow = {
            "provider": normalized_provider,
            "id": model_id,
            "ref": build_model_catalog_ref(normalized_provider, model_id),
            "mergeKey": build_model_catalog_merge_key(normalized_provider, model_id),
            "name": normalize_optional_string(model.get("name")) or model_id,
            "source": source,
            "input": _normalize_model_catalog_inputs(model.get("input")) or list(_DEFAULT_MODEL_INPUT),
            "reasoning": model.get("reasoning") is True,
            "status": _normalize_model_catalog_status(model.get("status")) or _DEFAULT_MODEL_STATUS,
        }
        if api:
            row["api"] = api
        if base_url:
            row["baseUrl"] = base_url
        if headers:
            row["headers"] = headers
        if context_window is not None:
            row["contextWindow"] = context_window
        if context_tokens is not None:
            row["contextTokens"] = context_tokens
        if max_tokens is not None:
            row["maxTokens"] = max_tokens
        if cost:
            row["cost"] = cost
        if compat:
            row["compat"] = compat
        if media_input:
            row["mediaInput"] = media_input
        if status_reason:
            row["statusReason"] = status_reason
        if replaces:
            row["replaces"] = replaces
        if replaced_by:
            row["replacedBy"] = replaced_by
        if tags:
            row["tags"] = tags
        rows.append(row)
    return sorted(rows, key=lambda entry: (entry["provider"], entry["id"]))


def normalize_model_catalog_rows(
    *,
    providers: dict[str, ModelCatalogProvider],
    source: ModelCatalogSource,
) -> list[NormalizedModelCatalogRow]:
    rows = [
        row
        for provider, provider_catalog in providers.items()
        for row in normalize_model_catalog_provider_rows(
            provider=provider,
            provider_catalog=provider_catalog,
            source=source,
        )
    ]
    return sorted(rows, key=lambda entry: (entry["provider"], entry["id"]))


__all__ = [
    "normalize_model_catalog",
    "normalize_model_catalog_provider_rows",
    "normalize_model_catalog_rows",
]
