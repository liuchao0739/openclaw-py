"""LLM runtime API provider registry."""

from __future__ import annotations

from typing import TypeVar

from openclaw.llm.core import Model

from .types import (
    Api,
    ApiProvider,
    ApiProviderInternal,
    ApiStreamFunction,
    ApiStreamSimpleFunction,
    Context,
    RegisteredApiProvider,
    SimpleStreamOptions,
    StreamFunction,
    StreamOptions,
)

TApi = TypeVar("TApi", bound=Api)

_api_provider_registry: dict[str, RegisteredApiProvider] = {}


def _wrap_stream(
    api: TApi,
    stream: StreamFunction[StreamOptions],
) -> ApiStreamFunction:
    def wrapped(
        model: Model,
        context: Context,
        options: StreamOptions | None = None,
    ):
        if model.api != api:
            raise ValueError(f"Mismatched api: {model.api} expected {api}")
        return stream(model, context, options)  # type: ignore[arg-type]

    return wrapped


def _wrap_stream_simple(
    api: TApi,
    stream_simple: StreamFunction[SimpleStreamOptions],
) -> ApiStreamSimpleFunction:
    def wrapped(
        model: Model,
        context: Context,
        options: SimpleStreamOptions | None = None,
    ):
        if model.api != api:
            raise ValueError(f"Mismatched api: {model.api} expected {api}")
        return stream_simple(model, context, options)

    return wrapped


def register_api_provider(
    provider: ApiProvider,
    source_id: str | None = None,
) -> None:
    """Register or replace the provider implementation for an API id."""
    api = provider["api"]
    entry: RegisteredApiProvider = {
        "provider": {
            "api": api,
            "stream": _wrap_stream(api, provider["stream"]),
            "stream_simple": _wrap_stream_simple(api, provider["stream_simple"]),
        },
    }
    if source_id is not None:
        entry["source_id"] = source_id
    _api_provider_registry[api] = entry


def get_api_provider(api: Api) -> ApiProviderInternal | None:
    """Look up a registered API provider by API id."""
    entry = _api_provider_registry.get(api)
    return entry["provider"] if entry else None


def get_api_providers() -> list[ApiProviderInternal]:
    """List all currently registered API providers."""
    return [entry["provider"] for entry in _api_provider_registry.values()]


def unregister_api_providers(source_id: str) -> None:
    """Remove all providers registered by a plugin/source id."""
    for api, entry in list(_api_provider_registry.items()):
        if entry.get("source_id") == source_id:
            del _api_provider_registry[api]


def clear_api_providers() -> None:
    """Clear the registry for test teardown and runtime reset flows."""
    _api_provider_registry.clear()
