import copy
from typing import Any, Dict, List, Optional, Set, Union

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
    ModelCatalogMediaInputConfig,
    ModelCatalogModel,
    ModelCatalogOpenRouterRouting,
    ModelCatalogProvider,
    ModelCatalogSource,
    ModelCatalogStatus,
    ModelCatalogSuppression,
    ModelCatalogTieredCost,
    ModelCatalogVercelGatewayRouting,
    NormalizedModelCatalogRow,
    is_model_catalog_thinking_format,
)

MODEL_CATALOG_INPUTS: Set[str] = {"text", "image", "document"}
MODEL_CATALOG_DISCOVERY_MODES: Set[str] = {"static", "refreshable", "runtime"}
MODEL_CATALOG_STATUSES: Set[str] = {"available", "preview", "deprecated", "disabled"}
MODEL_CATALOG_API_SET: Set[str] = set(MODEL_CATALOG_APIS)
DEFAULT_MODEL_INPUT: List[ModelCatalogInput] = ["text"]
DEFAULT_MODEL_STATUS: ModelCatalogStatus = "available"


def _is_record(value: Any) -> bool:
    return isinstance(value, dict) and not isinstance(value, list)


def _is_blocked_object_key(key: str) -> bool:
    return key == "__proto__" or key == "prototype" or key == "constructor"


def _normalize_optional_string(value: Any) -> Optional[str]:
    if not isinstance(value, str):
        return None
    trimmed = value.strip()
    return trimmed if trimmed else None


def _normalize_trimmed_string_list(value: Any) -> List[str]:
    if not isinstance(value, list):
        return []
    result: List[str] = []
    for entry in value:
        normalized = _normalize_optional_string(entry)
        if normalized:
            result.append(normalized)
    return result


def _normalize_optional_trimmed_string_list(value: Any) -> Optional[List[str]]:
    normalized = _normalize_trimmed_string_list(value)
    return normalized if len(normalized) > 0 else None


def _normalize_safe_record_key(value: Any) -> str:
    key = _normalize_optional_string(value) or ""
    return key if (key and not _is_blocked_object_key(key)) else ""


def _normalize_owned_provider_set(providers) -> Set[str]:
    normalized: Set[str] = set()
    for provider in providers:
        provider_id = normalize_model_catalog_provider_id(provider)
        if provider_id:
            normalized.add(provider_id)
    return normalized


def _normalize_string_map(value: Any) -> Optional[Dict[str, str]]:
    if not _is_record(value):
        return None
    normalized: Dict[str, str] = {}
    for raw_key, raw_value in value.items():
        key = _normalize_safe_record_key(raw_key)
        map_value = _normalize_optional_string(raw_value) or ""
        if key and map_value:
            normalized[key] = map_value
    return normalized if len(normalized) > 0 else None


def _merge_string_maps(
    base: Optional[Dict[str, str]],
    override: Optional[Dict[str, str]],
) -> Optional[Dict[str, str]]:
    if not base and not override:
        return None
    merged: Dict[str, str] = {}
    if base:
        merged.update(base)
    if override:
        merged.update(override)
    return merged


def _normalize_model_catalog_api(value: Any) -> Optional[ModelCatalogApi]:
    api = _normalize_optional_string(value) or ""
    return api if api in MODEL_CATALOG_API_SET else None


def _normalize_model_catalog_inputs(value: Any) -> Optional[List[ModelCatalogInput]]:
    inputs = [
        input_val
        for input_val in _normalize_trimmed_string_list(value)
        if input_val in MODEL_CATALOG_INPUTS
    ]
    return inputs if len(inputs) > 0 else None


def _normalize_non_negative_number(value: Any) -> Optional[float]:
    if isinstance(value, (int, float)) and not isinstance(value, bool) and value == value and value >= 0:
        return value
    return None


def _normalize_finite_number(value: Any) -> Optional[float]:
    if isinstance(value, (int, float)) and not isinstance(value, bool) and value == value:
        return value
    return None


def _normalize_string_or_number(value: Any) -> Optional[Union[str, float]]:
    return _normalize_optional_string(value) or _normalize_finite_number(value)


def _normalize_positive_number(value: Any) -> Optional[float]:
    if isinstance(value, (int, float)) and not isinstance(value, bool) and value == value and value > 0:
        return value
    return None


def _normalize_positive_integer(value: Any) -> Optional[int]:
    if isinstance(value, int) and not isinstance(value, bool) and value > 0:
        return value
    return None


def _normalize_model_catalog_tiered_cost(value: Any) -> Optional[List[ModelCatalogTieredCost]]:
    if not isinstance(value, list):
        return None
    normalized: List[ModelCatalogTieredCost] = []
    for entry in value:
        if not _is_record(entry) or not isinstance(entry.get("range"), list):
            continue
        input_val = _normalize_non_negative_number(entry.get("input"))
        output = _normalize_non_negative_number(entry.get("output"))
        cache_read = _normalize_non_negative_number(entry.get("cacheRead"))
        cache_write = _normalize_non_negative_number(entry.get("cacheWrite"))
        if (
            input_val is None
            or output is None
            or cache_read is None
            or cache_write is None
            or len(entry["range"]) < 1
            or len(entry["range"]) > 2
        ):
            continue
        range_values = [_normalize_non_negative_number(rv) for rv in entry["range"]]
        if any(rv is None for rv in range_values):
            continue
        tiered: ModelCatalogTieredCost = {
            "input": input_val,
            "output": output,
            "cacheRead": cache_read,
            "cacheWrite": cache_write,
            "range": (range_values[0],) if len(range_values) == 1 else (range_values[0], range_values[1]),
        }
        normalized.append(tiered)
    return normalized if len(normalized) > 0 else None


def _normalize_model_catalog_cost(value: Any) -> Optional[ModelCatalogCost]:
    if not _is_record(value):
        return None
    input_val = _normalize_non_negative_number(value.get("input"))
    output = _normalize_non_negative_number(value.get("output"))
    cache_read = _normalize_non_negative_number(value.get("cacheRead"))
    cache_write = _normalize_non_negative_number(value.get("cacheWrite"))
    tiered_pricing = _normalize_model_catalog_tiered_cost(value.get("tieredPricing"))
    cost: ModelCatalogCost = {}
    if input_val is not None:
        cost["input"] = input_val
    if output is not None:
        cost["output"] = output
    if cache_read is not None:
        cost["cacheRead"] = cache_read
    if cache_write is not None:
        cost["cacheWrite"] = cache_write
    if tiered_pricing:
        cost["tieredPricing"] = tiered_pricing
    return cost if len(cost) > 0 else None


def _normalize_open_router_price(value: Any) -> Optional[dict]:
    if not _is_record(value):
        return None
    max_price: dict = {}
    for field in ("prompt", "completion", "image", "audio", "request"):
        normalized = _normalize_string_or_number(value.get(field))
        if normalized is not None:
            max_price[field] = normalized
    return max_price if len(max_price) > 0 else None


def _normalize_open_router_percentile_cutoffs(value: Any) -> Optional[dict]:
    if not _is_record(value):
        return None
    normalized: dict = {}
    for field in ("p50", "p75", "p90", "p99"):
        val = _normalize_finite_number(value.get(field))
        if val is not None:
            normalized[field] = val
    return normalized if len(normalized) > 0 else None


def _normalize_open_router_metric_preference(value: Any) -> Optional[Union[float, dict]]:
    finite = _normalize_finite_number(value)
    if finite is not None:
        return finite
    return _normalize_open_router_percentile_cutoffs(value)


def _normalize_open_router_sort(value: Any) -> Optional[Union[str, dict]]:
    sort = _normalize_optional_string(value)
    if sort:
        return sort
    if not _is_record(value):
        return None
    by = _normalize_optional_string(value.get("by"))
    partition_raw = value.get("partition")
    if partition_raw is None:
        partition = None
    else:
        partition = _normalize_optional_string(partition_raw)
    normalized: dict = {}
    if by:
        normalized["by"] = by
    if partition is not None:
        normalized["partition"] = partition
    return normalized if len(normalized) > 0 else None


def _normalize_open_router_routing(value: Any) -> Optional[ModelCatalogOpenRouterRouting]:
    if not _is_record(value):
        return None
    routing: ModelCatalogOpenRouterRouting = {}
    if isinstance(value.get("allow_fallbacks"), bool):
        routing["allow_fallbacks"] = value["allow_fallbacks"]
    if isinstance(value.get("require_parameters"), bool):
        routing["require_parameters"] = value["require_parameters"]
    if value.get("data_collection") in ("deny", "allow"):
        routing["data_collection"] = value["data_collection"]
    if isinstance(value.get("zdr"), bool):
        routing["zdr"] = value["zdr"]
    if isinstance(value.get("enforce_distillable_text"), bool):
        routing["enforce_distillable_text"] = value["enforce_distillable_text"]
    order = _normalize_optional_trimmed_string_list(value.get("order"))
    if order:
        routing["order"] = order
    only = _normalize_optional_trimmed_string_list(value.get("only"))
    if only:
        routing["only"] = only
    ignore = _normalize_optional_trimmed_string_list(value.get("ignore"))
    if ignore:
        routing["ignore"] = ignore
    quantizations = _normalize_optional_trimmed_string_list(value.get("quantizations"))
    if quantizations:
        routing["quantizations"] = quantizations
    sort = _normalize_open_router_sort(value.get("sort"))
    if sort:
        routing["sort"] = sort
    max_price = _normalize_open_router_price(value.get("max_price"))
    if max_price:
        routing["max_price"] = max_price
    min_throughput = _normalize_open_router_metric_preference(value.get("preferred_min_throughput"))
    if min_throughput is not None:
        routing["preferred_min_throughput"] = min_throughput
    max_latency = _normalize_open_router_metric_preference(value.get("preferred_max_latency"))
    if max_latency is not None:
        routing["preferred_max_latency"] = max_latency
    return routing if len(routing) > 0 else None


def _normalize_vercel_gateway_routing(value: Any) -> Optional[ModelCatalogVercelGatewayRouting]:
    if not _is_record(value):
        return None
    routing: ModelCatalogVercelGatewayRouting = {}
    only = _normalize_optional_trimmed_string_list(value.get("only"))
    if only:
        routing["only"] = only
    order = _normalize_optional_trimmed_string_list(value.get("order"))
    if order:
        routing["order"] = order
    return routing if len(routing) > 0 else None


_COMPAT_BOOLEAN_FIELDS = [
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
]

_COMPAT_STRING_FIELDS = ["toolSchemaProfile", "toolCallArgumentsEncoding"]

_COMPAT_STRING_LIST_FIELDS = [
    "visibleReasoningDetailTypes",
    "supportedReasoningEfforts",
    "unsupportedToolSchemaKeywords",
]


def _normalize_model_catalog_compat(value: Any) -> Optional[ModelCatalogCompatConfig]:
    if not _is_record(value):
        return None
    compat: ModelCatalogCompatConfig = {}
    for field in _COMPAT_BOOLEAN_FIELDS:
        if isinstance(value.get(field), bool):
            compat[field] = value[field]

    for field in _COMPAT_STRING_FIELDS:
        normalized = _normalize_optional_string(value.get(field)) or ""
        if normalized:
            compat[field] = normalized

    for field in _COMPAT_STRING_LIST_FIELDS:
        normalized = _normalize_trimmed_string_list(value.get(field))
        if len(normalized) > 0:
            compat[field] = normalized

    if _is_record(value.get("reasoningEffortMap")):
        reasoning_effort_map: Dict[str, str] = {}
        for key, mapped in value["reasoningEffortMap"].items():
            trimmed_key = key.strip()
            trimmed_mapped = mapped.strip() if isinstance(mapped, str) else ""
            if len(trimmed_key) > 0 and len(trimmed_mapped) > 0:
                reasoning_effort_map[trimmed_key] = trimmed_mapped
        if len(reasoning_effort_map) > 0:
            compat["reasoningEffortMap"] = reasoning_effort_map

    max_tokens_field = _normalize_optional_string(value.get("maxTokensField")) or ""
    if max_tokens_field in ("max_completion_tokens", "max_tokens"):
        compat["maxTokensField"] = max_tokens_field

    thinking_format = _normalize_optional_string(value.get("thinkingFormat")) or ""
    if is_model_catalog_thinking_format(thinking_format):
        compat["thinkingFormat"] = thinking_format

    if value.get("cacheControlFormat") == "anthropic":
        compat["cacheControlFormat"] = "anthropic"

    open_router_routing = _normalize_open_router_routing(value.get("openRouterRouting"))
    if open_router_routing:
        compat["openRouterRouting"] = open_router_routing

    vercel_gateway_routing = _normalize_vercel_gateway_routing(value.get("vercelGatewayRouting"))
    if vercel_gateway_routing:
        compat["vercelGatewayRouting"] = vercel_gateway_routing

    return compat if len(compat) > 0 else None


def _normalize_model_catalog_status(value: Any) -> Optional[ModelCatalogStatus]:
    status = _normalize_optional_string(value) or ""
    return status if status in MODEL_CATALOG_STATUSES else None


def _normalize_model_catalog_image_token_mode(value: Any) -> Optional[str]:
    token_mode = _normalize_optional_string(value) or ""
    if token_mode in ("tile", "detail", "provider"):
        return token_mode
    return None


def _normalize_model_catalog_media_input(value: Any) -> Optional[ModelCatalogMediaInputConfig]:
    if not _is_record(value) or not _is_record(value.get("image")):
        return None
    image = value["image"]
    max_bytes = _normalize_positive_integer(image.get("maxBytes"))
    max_pixels = _normalize_positive_integer(image.get("maxPixels"))
    max_side_px = _normalize_positive_integer(image.get("maxSidePx"))
    preferred_side_px = _normalize_positive_integer(image.get("preferredSidePx"))
    token_mode = _normalize_model_catalog_image_token_mode(image.get("tokenMode"))
    normalized_image: dict = {}
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
    return {"image": normalized_image} if len(normalized_image) > 0 else None


def _normalize_model_catalog_model(value: Any) -> Optional[ModelCatalogModel]:
    if not _is_record(value):
        return None
    id = _normalize_optional_string(value.get("id")) or ""
    if not id:
        return None
    name = _normalize_optional_string(value.get("name")) or ""
    api = _normalize_model_catalog_api(value.get("api"))
    base_url = _normalize_optional_string(value.get("baseUrl")) or ""
    headers = _normalize_string_map(value.get("headers"))
    input_val = _normalize_model_catalog_inputs(value.get("input"))
    reasoning = value.get("reasoning") if isinstance(value.get("reasoning"), bool) else None
    context_window = _normalize_positive_number(value.get("contextWindow"))
    context_tokens = _normalize_positive_integer(value.get("contextTokens"))
    max_tokens = _normalize_positive_number(value.get("maxTokens"))
    cost = _normalize_model_catalog_cost(value.get("cost"))
    compat = _normalize_model_catalog_compat(value.get("compat"))
    media_input = _normalize_model_catalog_media_input(value.get("mediaInput"))
    status = _normalize_model_catalog_status(value.get("status"))
    status_reason = _normalize_optional_string(value.get("statusReason")) or ""
    replaces = _normalize_trimmed_string_list(value.get("replaces"))
    replaced_by = _normalize_optional_string(value.get("replacedBy")) or ""
    tags = _normalize_trimmed_string_list(value.get("tags"))
    model: ModelCatalogModel = {"id": id}
    if name:
        model["name"] = name
    if api:
        model["api"] = api
    if base_url:
        model["baseUrl"] = base_url
    if headers:
        model["headers"] = headers
    if input_val:
        model["input"] = input_val
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
    if len(replaces) > 0:
        model["replaces"] = replaces
    if replaced_by:
        model["replacedBy"] = replaced_by
    if len(tags) > 0:
        model["tags"] = tags
    return model


def _normalize_model_catalog_provider(value: Any) -> Optional[ModelCatalogProvider]:
    if not _is_record(value):
        return None
    models_raw = value.get("models")
    models: List[ModelCatalogModel] = []
    if isinstance(models_raw, list):
        for entry in models_raw:
            normalized = _normalize_model_catalog_model(entry)
            if normalized:
                models.append(normalized)
    if len(models) == 0:
        return None
    base_url = _normalize_optional_string(value.get("baseUrl")) or ""
    api = _normalize_model_catalog_api(value.get("api"))
    headers = _normalize_string_map(value.get("headers"))
    provider: ModelCatalogProvider = {"models": models}
    if base_url:
        provider["baseUrl"] = base_url
    if api:
        provider["api"] = api
    if headers:
        provider["headers"] = headers
    return provider


def _normalize_model_catalog_providers(
    value: Any,
    owned_providers,
) -> Optional[Dict[str, ModelCatalogProvider]]:
    if not _is_record(value):
        return None
    providers: Dict[str, ModelCatalogProvider] = {}
    for raw_provider_id, raw_provider in value.items():
        provider_id = normalize_model_catalog_provider_id(raw_provider_id)
        if not provider_id or provider_id not in owned_providers:
            continue
        provider = _normalize_model_catalog_provider(raw_provider)
        if provider:
            providers[provider_id] = provider
    return providers if len(providers) > 0 else None


def _normalize_model_catalog_aliases(
    value: Any,
    owned_providers,
) -> Optional[Dict[str, ModelCatalogAlias]]:
    if not _is_record(value):
        return None
    aliases: Dict[str, ModelCatalogAlias] = {}
    for raw_alias, raw_target in value.items():
        alias = normalize_model_catalog_provider_id(raw_alias)
        if not alias or not _is_record(raw_target):
            continue
        provider = normalize_model_catalog_provider_id(_normalize_optional_string(raw_target.get("provider")) or "")
        if not provider or provider not in owned_providers:
            continue
        api = _normalize_model_catalog_api(raw_target.get("api"))
        base_url = _normalize_optional_string(raw_target.get("baseUrl")) or ""
        alias_entry: ModelCatalogAlias = {"provider": provider}
        if api:
            alias_entry["api"] = api
        if base_url:
            alias_entry["baseUrl"] = base_url
        aliases[alias] = alias_entry
    return aliases if len(aliases) > 0 else None


def _normalize_model_catalog_suppressions(value: Any) -> Optional[List[ModelCatalogSuppression]]:
    if not isinstance(value, list):
        return None
    suppressions: List[ModelCatalogSuppression] = []
    for entry in value:
        if not _is_record(entry):
            continue
        provider = normalize_model_catalog_provider_id(_normalize_optional_string(entry.get("provider")) or "")
        model = _normalize_optional_string(entry.get("model")) or ""
        if not provider or not model:
            continue
        reason = _normalize_optional_string(entry.get("reason")) or ""
        raw_when = entry.get("when") if _is_record(entry.get("when")) else None
        base_url_hosts = [h.lower() for h in _normalize_trimmed_string_list(raw_when.get("baseUrlHosts") if raw_when else None)]
        provider_config_api_in = [a.lower() for a in _normalize_trimmed_string_list(raw_when.get("providerConfigApiIn") if raw_when else None)]
        when: Optional[dict] = None
        if len(base_url_hosts) > 0 or len(provider_config_api_in) > 0:
            when = {}
            if len(base_url_hosts) > 0:
                when["baseUrlHosts"] = base_url_hosts
            if len(provider_config_api_in) > 0:
                when["providerConfigApiIn"] = provider_config_api_in
        suppression: ModelCatalogSuppression = {"provider": provider, "model": model}
        if reason:
            suppression["reason"] = reason
        if when:
            suppression["when"] = when
        suppressions.append(suppression)
    return suppressions if len(suppressions) > 0 else None


def _normalize_model_catalog_discovery(
    value: Any,
    owned_providers,
) -> Optional[Dict[str, ModelCatalogDiscovery]]:
    if not _is_record(value):
        return None
    discovery: Dict[str, ModelCatalogDiscovery] = {}
    for raw_provider_id, raw_mode in value.items():
        provider_id = normalize_model_catalog_provider_id(raw_provider_id)
        mode = _normalize_optional_string(raw_mode) or ""
        if provider_id and provider_id in owned_providers and mode in MODEL_CATALOG_DISCOVERY_MODES:
            discovery[provider_id] = mode
    return discovery if len(discovery) > 0 else None


def normalize_model_catalog(
    value: Any,
    params: dict,
) -> Optional[ModelCatalog]:
    if not _is_record(value):
        return None
    owned_providers = _normalize_owned_provider_set(params["ownedProviders"])
    providers = _normalize_model_catalog_providers(value.get("providers"), owned_providers)
    aliases = _normalize_model_catalog_aliases(value.get("aliases"), owned_providers)
    suppressions = _normalize_model_catalog_suppressions(value.get("suppressions"))
    discovery = _normalize_model_catalog_discovery(value.get("discovery"), owned_providers)
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
        catalog["runtimeAugment"] = runtime_augment
    return catalog if len(catalog) > 0 else None


def normalize_model_catalog_provider_rows(params: dict) -> List[NormalizedModelCatalogRow]:
    provider = normalize_model_catalog_provider_id(params["provider"])
    provider_catalog = params["providerCatalog"]
    if not provider or not isinstance(provider_catalog.get("models"), list):
        return []
    provider_api = _normalize_model_catalog_api(provider_catalog.get("api"))
    provider_base_url = _normalize_optional_string(provider_catalog.get("baseUrl")) or ""
    provider_headers = _normalize_string_map(provider_catalog.get("headers"))
    rows: List[NormalizedModelCatalogRow] = []

    for model in provider_catalog["models"]:
        id = _normalize_optional_string(model.get("id")) or ""
        if not id:
            continue
        api = _normalize_model_catalog_api(model.get("api")) or provider_api
        base_url = _normalize_optional_string(model.get("baseUrl")) or provider_base_url
        headers = _merge_string_maps(provider_headers, _normalize_string_map(model.get("headers")))
        context_window = _normalize_positive_number(model.get("contextWindow"))
        context_tokens = _normalize_positive_integer(model.get("contextTokens"))
        max_tokens = _normalize_positive_number(model.get("maxTokens"))
        cost = _normalize_model_catalog_cost(model.get("cost"))
        compat = _normalize_model_catalog_compat(model.get("compat"))
        media_input = _normalize_model_catalog_media_input(model.get("mediaInput"))
        status_reason = _normalize_optional_string(model.get("statusReason")) or ""
        replaced_by = _normalize_optional_string(model.get("replacedBy")) or ""
        replaces = _normalize_optional_trimmed_string_list(model.get("replaces"))
        tags = _normalize_optional_trimmed_string_list(model.get("tags"))
        row: NormalizedModelCatalogRow = {
            "provider": provider,
            "id": id,
            "ref": build_model_catalog_ref(provider, id),
            "mergeKey": build_model_catalog_merge_key(provider, id),
            "name": _normalize_optional_string(model.get("name")) or id,
            "source": params["source"],
            "input": _normalize_model_catalog_inputs(model.get("input")) or list(DEFAULT_MODEL_INPUT),
            "reasoning": model.get("reasoning") if isinstance(model.get("reasoning"), bool) else False,
            "status": _normalize_model_catalog_status(model.get("status")) or DEFAULT_MODEL_STATUS,
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

    rows.sort(key=lambda r: (r["provider"], r["id"]))
    return rows


def normalize_model_catalog_rows(params: dict) -> List[NormalizedModelCatalogRow]:
    rows: List[NormalizedModelCatalogRow] = []
    for provider, provider_catalog in params["providers"].items():
        rows.extend(
            normalize_model_catalog_provider_rows({
                "provider": provider,
                "providerCatalog": provider_catalog,
                "source": params["source"],
            })
        )
    rows.sort(key=lambda r: (r["provider"], r["id"]))
    return rows
