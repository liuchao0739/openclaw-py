"""Chutes model catalog, static model definitions, and dynamic model discovery."""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any

from openclaw.packages.normalization_core import (
    as_positive_safe_integer,
    normalize_lowercase_string_or_empty,
    normalize_optional_string,
)
from openclaw.plugin_sdk.provider_catalog_live_runtime import (
    LiveModelCatalogHttpError,
    clear_live_catalog_cache_for_tests,
    get_cached_live_provider_model_rows,
    ssrf_policy_from_http_base_url_allowed_hostname,
)
from openclaw.plugin_sdk.provider_catalog_shared import ModelDefinitionConfig
from openclaw_extensions.chutes.model_discovery_env import (
    is_chutes_model_discovery_test_environment,
)

_log = logging.getLogger("chutes-models")

CHUTES_BASE_URL = "https://llm.chutes.ai/v1"
CHUTES_DEFAULT_MODEL_ID = "zai-org/GLM-4.7-TEE"
CHUTES_DEFAULT_MODEL_REF = f"chutes/{CHUTES_DEFAULT_MODEL_ID}"

_CHUTES_DEFAULT_CONTEXT_WINDOW = 128_000
_CHUTES_DEFAULT_MAX_TOKENS = 4096
_CACHE_TTL_MS = 5 * 60 * 1000
_discovery_now: Callable[[], int] | None = None

_MANIFEST_PATH = Path(__file__).resolve().parent / "openclaw.plugin.json"
_MANIFEST = json.loads(_MANIFEST_PATH.read_text(encoding="utf-8"))
_CHUTES_MANIFEST_CATALOG = _MANIFEST["modelCatalog"]["providers"]["chutes"]

CHUTES_MODEL_CATALOG: list[ModelDefinitionConfig] = _CHUTES_MANIFEST_CATALOG["models"]


def build_chutes_model_definition(model: ModelDefinitionConfig) -> ModelDefinitionConfig:
    """Add Chutes provider compat metadata to one model catalog entry."""
    return {
        **model,
        "compat": {
            "supportsUsageInStreaming": False,
        },
    }


def clear_chutes_model_cache_for_tests() -> None:
    """Clear the dynamic Chutes model discovery cache for tests."""
    clear_live_catalog_cache_for_tests()


async def _fetch_chutes_model_rows(access_token: str | None = None) -> list[Any]:
    params: dict[str, Any] = {
        "providerId": "chutes",
        "endpoint": f"{CHUTES_BASE_URL}/models",
        "discoveryApiKey": access_token,
        "timeoutMs": 10_000,
        "ttlMs": _CACHE_TTL_MS,
        "buildRequestHeaders": lambda ctx: {
            "Accept": "application/json",
            **(
                {"Authorization": f"Bearer {ctx['discoveryApiKey']}"}
                if ctx.get("discoveryApiKey")
                else {}
            ),
        },
        "policy": ssrf_policy_from_http_base_url_allowed_hostname(CHUTES_BASE_URL),
        "auditContext": "chutes-model-discovery",
    }
    if _discovery_now is not None:
        params["now"] = _discovery_now
    return await get_cached_live_provider_model_rows(params)


async def discover_chutes_models(access_token: str | None = None) -> list[ModelDefinitionConfig]:
    """Discover Chutes models dynamically, falling back to the bundled static catalog."""
    trimmed_key = normalize_optional_string(access_token) or ""

    if is_chutes_model_discovery_test_environment():
        return [build_chutes_model_definition(model) for model in CHUTES_MODEL_CATALOG]

    def static_catalog() -> list[ModelDefinitionConfig]:
        return [build_chutes_model_definition(model) for model in CHUTES_MODEL_CATALOG]

    try:
        data = await _fetch_chutes_model_rows(trimmed_key or None)
        if len(data) == 0:
            _log.warning("No models in response, using static catalog")
            return static_catalog()

        seen: set[str] = set()
        models: list[ModelDefinitionConfig] = []

        for entry in data:
            if not isinstance(entry, dict):
                continue
            model_id = normalize_optional_string(entry.get("id")) or ""
            if not model_id or model_id in seen:
                continue
            seen.add(model_id)

            lower_id = normalize_lowercase_string_or_empty(model_id)
            supported_features = entry.get("supported_features")
            is_reasoning = (
                isinstance(supported_features, list) and "reasoning" in supported_features
            ) or any(
                token in lower_id
                for token in ("r1", "thinking", "reason", "tee")
            )

            raw_input = entry.get("input_modalities") or ["text"]
            input_modes = [
                item for item in raw_input if item in ("text", "image")
            ] if isinstance(raw_input, list) else ["text"]

            pricing = entry.get("pricing")
            pricing_dict = pricing if isinstance(pricing, dict) else {}
            models.append(
                {
                    "id": model_id,
                    "name": model_id,
                    "reasoning": is_reasoning,
                    "input": input_modes,
                    "cost": {
                        "input": pricing_dict.get("prompt") or 0,
                        "output": pricing_dict.get("completion") or 0,
                        "cacheRead": 0,
                        "cacheWrite": 0,
                    },
                    "contextWindow": as_positive_safe_integer(entry.get("context_length"))
                    or _CHUTES_DEFAULT_CONTEXT_WINDOW,
                    "maxTokens": as_positive_safe_integer(entry.get("max_output_length"))
                    or _CHUTES_DEFAULT_MAX_TOKENS,
                    "compat": {
                        "supportsUsageInStreaming": False,
                    },
                }
            )

        if len(models) == 0:
            return static_catalog()
        return models
    except LiveModelCatalogHttpError as error:
        if error.status == 401 and trimmed_key:
            return await discover_chutes_models(None)
        if error.status not in (401, 503):
            _log.warning("GET /v1/models failed: HTTP %s, using static catalog", error.status)
        else:
            _log.warning("Discovery failed: %s, using static catalog", error)
        return static_catalog()
    except Exception as error:  # noqa: BLE001
        _log.warning("Discovery failed: %s, using static catalog", error)
        return static_catalog()
