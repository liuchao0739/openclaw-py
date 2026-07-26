"""Tests for the brave web search provider."""

from __future__ import annotations

import json
from typing import Any
from urllib.parse import parse_qs, urlparse

import httpx
import pytest

from openclaw.plugin_sdk.provider_web_search import SEARCH_CACHE
from openclaw_extensions.brave.src import brave_web_search_provider_runtime as runtime_module
from openclaw_extensions.brave.src.brave_web_search_provider import create_brave_web_search_provider
from openclaw_extensions.brave.src.config import brave_plugin_config_schema
from openclaw_extensions.brave.test_api import testing
from openclaw_extensions.brave.web_search_contract_api import (
    create_brave_web_search_provider as create_brave_web_search_contract_provider,
)


class _StreamReader:
    def __init__(self, chunk_count: int, chunk_size: int, *, text: str = "x") -> None:
        self._chunk_count = chunk_count
        self._chunk_size = chunk_size
        self._text = text
        self._reads = 0
        self._canceled = False

    async def read(self) -> tuple[bytes, bool]:
        if self._reads >= self._chunk_count:
            return b"", True
        self._reads += 1
        return (self._text * self._chunk_size).encode("utf-8"), False

    async def cancel(self) -> None:
        self._canceled = True


class _StreamingBody:
    def __init__(self, reader: _StreamReader) -> None:
        self._reader = reader

    def get_reader(self) -> _StreamReader:
        return self._reader


class _StreamingResponse:
    def __init__(self, reader: _StreamReader, *, status: int = 429) -> None:
        self.body = _StreamingBody(reader)
        self._reader = reader
        self.status_code = status
        self.status = status
        self.ok = False
        self.is_success = False
        self.reason_phrase = "Too Many Requests"
        self.headers = {}

    async def text(self) -> str:
        raise RuntimeError("unbounded")

    async def aread(self) -> bytes:
        raise RuntimeError("unbounded")


@pytest.fixture(autouse=True)
def reset_brave_state(monkeypatch: pytest.MonkeyPatch) -> None:
    import openclaw_extensions.brave.src.brave_web_search_provider as provider_module

    SEARCH_CACHE.clear()
    runtime_module.brave_http_log_records.clear()
    monkeypatch.setattr(provider_module, "_brave_runtime_module", None)
    monkeypatch.delenv("BRAVE_API_KEY", raising=False)


def _json_response(payload: Any, *, status: int = 200) -> httpx.Response:
    return httpx.Response(
        status,
        content=json.dumps(payload).encode("utf-8"),
        headers={"content-type": "application/json"},
    )


def _empty_web_search_response() -> httpx.Response:
    return _json_response({"web": {"results": []}})


def _install_brave_fetch(monkeypatch: pytest.MonkeyPatch, handler: Any) -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = []

    async def fake_with_trusted(params: dict[str, Any], run: Any) -> Any:
        calls.append(params)
        response = handler(params)
        if hasattr(response, "__await__"):
            response = await response
        return await run(response)

    monkeypatch.setattr(runtime_module, "with_trusted_web_search_endpoint", fake_with_trusted)
    return calls


def _request_url(calls: list[dict[str, Any]], index: int = 0) -> str:
    return calls[index]["url"]


def _request_headers(calls: list[dict[str, Any]], index: int = 0) -> dict[str, str]:
    init = calls[index].get("init") or {}
    headers = init.get("headers") or {}
    return {str(key): str(value) for key, value in headers.items()}


def test_points_provider_metadata_at_canonical_brave_docs_page() -> None:
    assert (
        create_brave_web_search_provider()["docs_url"]
        == "https://docs.openclaw.ai/tools/brave-search"
    )
    assert (
        create_brave_web_search_contract_provider()["docs_url"]
        == "https://docs.openclaw.ai/tools/brave-search"
    )


def test_exposes_legacy_top_level_api_key_as_brave_owned_compatibility_fallback() -> None:
    api_key = {"source": "env", "provider": "default", "id": "BRAVE_API_KEY"}
    config = {"tools": {"web": {"search": {"apiKey": api_key}}}}

    provider = create_brave_web_search_provider()
    contract_provider = create_brave_web_search_contract_provider()

    assert provider["get_configured_credential_value"](config) == api_key
    assert contract_provider["get_configured_credential_value"](config) == api_key
    assert provider["get_configured_credential_fallback"](config) == {
        "path": "tools.web.search.apiKey",
        "value": api_key,
    }
    assert contract_provider["get_configured_credential_fallback"](config) == {
        "path": "tools.web.search.apiKey",
        "value": api_key,
    }


@pytest.mark.asyncio
async def test_points_missing_key_users_to_fetch_browser_alternatives(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("BRAVE_API_KEY", "")
    provider = create_brave_web_search_provider()
    tool = provider["create_tool"]({"config": {}, "search_config": {}})
    assert tool is not None

    result = await tool["execute"]({"query": "OpenClaw docs"})

    assert result == {
        "error": "missing_brave_api_key",
        "message": (
            "web_search (brave) needs a Brave Search API key. Run "
            "`openclaw configure --section web` to store it, or set BRAVE_API_KEY in the "
            "Gateway environment. If you do not want to configure a search API key, use "
            "web_fetch for a specific URL or the browser tool for interactive pages."
        ),
        "docs": "https://docs.openclaw.ai/tools/web",
    }


def test_normalizes_brave_language_parameters_and_swaps_reversed_ui_search_inputs() -> None:
    assert testing["normalize_brave_language_params"](
        {"search_lang": "en-US", "ui_lang": "ja"}
    ) == {"search_lang": "jp", "ui_lang": "en-US"}
    assert testing["normalize_brave_language_params"](
        {"search_lang": "tr-TR", "ui_lang": "tr"}
    ) == {"search_lang": "tr", "ui_lang": "tr-TR"}
    assert testing["normalize_brave_language_params"](
        {"search_lang": "EN", "ui_lang": "en-us"}
    ) == {"search_lang": "en", "ui_lang": "en-US"}


def test_flags_invalid_brave_language_fields() -> None:
    assert testing["normalize_brave_language_params"]({"search_lang": "xx"}) == {
        "invalidField": "search_lang"
    }
    assert testing["normalize_brave_language_params"]({"search_lang": "en-US"}) == {
        "invalidField": "search_lang"
    }
    assert testing["normalize_brave_language_params"]({"ui_lang": "en"}) == {
        "invalidField": "ui_lang"
    }


def test_normalizes_brave_country_codes_and_falls_back_unsupported_values_to_all() -> None:
    assert testing["normalize_brave_country"]("de") == "DE"
    assert testing["normalize_brave_country"](" VN ") == "ALL"
    assert testing["normalize_brave_country"]("") is None


def test_defaults_brave_mode_to_web_unless_llm_context_is_explicitly_selected() -> None:
    assert testing["resolve_brave_mode"]() == "web"
    assert testing["resolve_brave_mode"]({"mode": "llm-context"}) == "llm-context"


def test_accepts_llm_context_in_brave_plugin_config_schema() -> None:
    result = brave_plugin_config_schema["safeParse"]({"webSearch": {"mode": "llm-context"}})
    assert result["success"] is True


def test_accepts_base_url_in_brave_plugin_config_schema() -> None:
    result = brave_plugin_config_schema["safeParse"](
        {"webSearch": {"baseUrl": "https://api.search.brave.com/proxy"}}
    )
    assert result["success"] is True


@pytest.mark.asyncio
async def test_uses_configured_brave_base_url_for_web_search_requests(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = _install_brave_fetch(monkeypatch, lambda _params: _empty_web_search_response())
    provider = create_brave_web_search_provider()
    tool = provider["create_tool"](
        {
            "config": {},
            "search_config": {
                "apiKey": "brave-test-key",
                "brave": {
                    "baseUrl": "https://api.search.brave.com/proxy/",
                    "mode": "web",
                },
            },
        }
    )
    assert tool is not None

    await tool["execute"]({"query": "latest ai news"})

    request_url = urlparse(_request_url(calls))
    assert request_url.netloc == "api.search.brave.com"
    assert request_url.path == "/proxy/res/v1/web/search"


@pytest.mark.asyncio
async def test_uses_configured_brave_base_url_for_llm_context_requests(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = _install_brave_fetch(
        monkeypatch,
        lambda _params: _json_response(
            {
                "grounding": {
                    "generic": [
                        {
                            "url": "https://example.com/context",
                            "title": "Context",
                            "snippets": ["snippet"],
                        }
                    ]
                },
                "sources": [],
            }
        ),
    )
    provider = create_brave_web_search_provider()
    tool = provider["create_tool"](
        {
            "config": {},
            "search_config": {
                "apiKey": "brave-test-key",
                "brave": {
                    "baseUrl": "https://api.search.brave.com/proxy",
                    "mode": "llm-context",
                },
            },
        }
    )
    assert tool is not None

    await tool["execute"]({"query": "latest ai news"})

    assert urlparse(_request_url(calls)).path == "/proxy/res/v1/llm/context"


@pytest.mark.asyncio
async def test_reports_malformed_brave_web_search_json_as_provider_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_brave_fetch(
        monkeypatch,
        lambda _params: httpx.Response(
            200, content=b"{ nope", headers={"content-type": "application/json"}
        ),
    )
    provider = create_brave_web_search_provider()
    tool = provider["create_tool"](
        {
            "config": {},
            "search_config": {"apiKey": "brave-test-key", "brave": {"mode": "web"}},
        }
    )
    assert tool is not None

    with pytest.raises(RuntimeError, match="Brave Search API error: malformed JSON response"):
        await tool["execute"]({"query": "latest ai news"})


@pytest.mark.asyncio
async def test_reports_malformed_brave_llm_context_json_as_provider_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_brave_fetch(
        monkeypatch,
        lambda _params: httpx.Response(
            200, content=b"{ nope", headers={"content-type": "application/json"}
        ),
    )
    provider = create_brave_web_search_provider()
    tool = provider["create_tool"](
        {
            "config": {},
            "search_config": {"apiKey": "brave-test-key", "brave": {"mode": "llm-context"}},
        }
    )
    assert tool is not None

    with pytest.raises(RuntimeError, match="Brave LLM Context API error: malformed JSON response"):
        await tool["execute"]({"query": "latest ai news"})


@pytest.mark.asyncio
async def test_bounds_brave_web_error_bodies_without_using_response_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reader = _StreamReader(1, 24 * 1024, text="x")

    async def handler(_params: dict[str, Any]) -> _StreamingResponse:
        return _StreamingResponse(reader)

    _install_brave_fetch(monkeypatch, handler)
    provider = create_brave_web_search_provider()
    tool = provider["create_tool"](
        {
            "config": {},
            "search_config": {"apiKey": "brave-test-key", "brave": {"mode": "web"}},
        }
    )
    assert tool is not None

    with pytest.raises(RuntimeError) as exc_info:
        await tool["execute"]({"query": "latest ai news"})

    message = str(exc_info.value)
    assert "Brave Search API error (429):" in message
    assert "tail" not in message
    assert len(message) < 700


@pytest.mark.asyncio
async def test_bounds_brave_llm_context_error_bodies_without_using_response_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reader = _StreamReader(1, 24 * 1024, text="x")

    async def handler(_params: dict[str, Any]) -> _StreamingResponse:
        return _StreamingResponse(reader)

    _install_brave_fetch(monkeypatch, handler)
    provider = create_brave_web_search_provider()
    tool = provider["create_tool"](
        {
            "config": {},
            "search_config": {"apiKey": "brave-test-key", "brave": {"mode": "llm-context"}},
        }
    )
    assert tool is not None

    with pytest.raises(RuntimeError) as exc_info:
        await tool["execute"]({"query": "latest ai news"})

    message = str(exc_info.value)
    assert "Brave LLM Context API error (429):" in message
    assert "tail" not in message
    assert len(message) < 700


@pytest.mark.asyncio
async def test_keeps_brave_cache_entries_isolated_by_base_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = _install_brave_fetch(monkeypatch, lambda _params: _empty_web_search_response())
    provider = create_brave_web_search_provider()
    first_tool = provider["create_tool"](
        {
            "config": {},
            "search_config": {
                "apiKey": "brave-test-key",
                "brave": {
                    "baseUrl": "https://api.search.brave.com/proxy-one",
                    "mode": "web",
                },
            },
        }
    )
    second_tool = provider["create_tool"](
        {
            "config": {},
            "search_config": {
                "apiKey": "brave-test-key",
                "brave": {
                    "baseUrl": "https://api.search.brave.com/proxy-two",
                    "mode": "web",
                },
            },
        }
    )
    assert first_tool is not None and second_tool is not None

    await first_tool["execute"]({"query": "base url cache identity"})
    await second_tool["execute"]({"query": "base url cache identity"})

    assert len(calls) == 2
    assert urlparse(_request_url(calls, 0)).path == "/proxy-one/res/v1/web/search"
    assert urlparse(_request_url(calls, 1)).path == "/proxy-two/res/v1/web/search"


def test_rejects_invalid_brave_mode_values_in_plugin_config_schema() -> None:
    result = brave_plugin_config_schema["safeParse"]({"webSearch": {"mode": "invalid-mode"}})
    assert result["success"] is False
    issues = result["error"]["issues"]
    assert issues[0]["path"] == ["webSearch", "mode"]
    assert 'allowed: "web", "llm-context"' in issues[0]["message"]


def test_maps_llm_context_results_into_wrapped_source_entries() -> None:
    assert testing["map_brave_llm_context_results"](
        {
            "grounding": {
                "generic": [
                    {
                        "url": "https://example.com/post",
                        "title": "Example",
                        "snippets": ["a", "", "b"],
                    }
                ]
            }
        }
    ) == [
        {
            "url": "https://example.com/post",
            "title": "Example",
            "snippets": ["a", "b"],
            "siteName": "example.com",
        }
    ]


@pytest.mark.asyncio
async def test_returns_validation_errors_for_invalid_date_ranges() -> None:
    provider = create_brave_web_search_provider()
    tool = provider["create_tool"](
        {
            "config": {},
            "search_config": {"apiKey": "BSA...", "brave": {"apiKey": "BSA..."}},
        }
    )
    assert tool is not None

    result = await tool["execute"](
        {
            "query": "latest gpu news",
            "date_after": "2026-03-20",
            "date_before": "2026-03-01",
        }
    )

    assert result == {
        "error": "invalid_date_range",
        "message": "date_after must be before date_before.",
        "docs": "https://docs.openclaw.ai/tools/web",
    }


@pytest.mark.asyncio
async def test_passes_freshness_to_brave_llm_context_endpoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("BRAVE_API_KEY", "test-key")
    calls = _install_brave_fetch(
        monkeypatch,
        lambda _params: _json_response({"grounding": {"generic": []}, "sources": []}),
    )
    provider = create_brave_web_search_provider()
    tool = provider["create_tool"](
        {
            "config": {},
            "search_config": {"apiKey": "BSA...", "brave": {"mode": "llm-context"}},
        }
    )
    assert tool is not None

    await tool["execute"]({"query": "latest ai news", "freshness": "week"})

    query = parse_qs(urlparse(_request_url(calls)).query)
    assert urlparse(_request_url(calls)).path == "/res/v1/llm/context"
    assert query["freshness"] == ["pw"]


@pytest.mark.asyncio
async def test_sends_brave_web_auth_in_x_subscription_token_header(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = _install_brave_fetch(monkeypatch, lambda _params: _empty_web_search_response())
    provider = create_brave_web_search_provider()
    tool = provider["create_tool"](
        {
            "config": {},
            "search_config": {"apiKey": "brave-test-key", "brave": {"mode": "web"}},
        }
    )
    assert tool is not None

    await tool["execute"]({"query": "latest ai news"})

    query = parse_qs(urlparse(_request_url(calls)).query)
    assert "apikey" not in query
    assert "key" not in query
    assert _request_headers(calls)["X-Subscription-Token"] == "brave-test-key"


@pytest.mark.asyncio
async def test_sends_brave_llm_context_auth_in_x_subscription_token_header(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = _install_brave_fetch(
        monkeypatch,
        lambda _params: _json_response({"grounding": {"generic": []}, "sources": []}),
    )
    provider = create_brave_web_search_provider()
    tool = provider["create_tool"](
        {
            "config": {},
            "search_config": {"apiKey": "brave-test-key", "brave": {"mode": "llm-context"}},
        }
    )
    assert tool is not None

    await tool["execute"]({"query": "latest ai news"})

    query = parse_qs(urlparse(_request_url(calls)).query)
    assert "apikey" not in query
    assert "key" not in query
    assert _request_headers(calls)["X-Subscription-Token"] == "brave-test-key"


@pytest.mark.asyncio
async def test_passes_bounded_date_ranges_to_brave_llm_context_endpoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("BRAVE_API_KEY", "test-key")
    calls = _install_brave_fetch(
        monkeypatch,
        lambda _params: _json_response({"grounding": {"generic": []}, "sources": []}),
    )
    provider = create_brave_web_search_provider()
    tool = provider["create_tool"](
        {
            "config": {},
            "search_config": {"apiKey": "BSA...", "brave": {"mode": "llm-context"}},
        }
    )
    assert tool is not None

    await tool["execute"](
        {
            "query": "latest ai news",
            "date_after": "2025-01-01",
            "date_before": "2025-01-31",
        }
    )

    query = parse_qs(urlparse(_request_url(calls)).query)
    assert urlparse(_request_url(calls)).path == "/res/v1/llm/context"
    assert query["freshness"] == ["2025-01-01to2025-01-31"]


@pytest.mark.asyncio
async def test_uses_today_as_end_date_for_brave_llm_context_date_after_only_ranges(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("BRAVE_API_KEY", "test-key")
    calls = _install_brave_fetch(
        monkeypatch,
        lambda _params: _json_response({"grounding": {"generic": []}, "sources": []}),
    )
    provider = create_brave_web_search_provider()
    tool = provider["create_tool"](
        {
            "config": {},
            "search_config": {"apiKey": "BSA...", "brave": {"mode": "llm-context"}},
        }
    )
    assert tool is not None

    await tool["execute"]({"query": "latest ai news", "date_after": "2025-01-01"})

    from datetime import UTC, datetime

    today = datetime.now(UTC).date().isoformat()
    query = parse_qs(urlparse(_request_url(calls)).query)
    assert urlparse(_request_url(calls)).path == "/res/v1/llm/context"
    assert query["freshness"] == [f"2025-01-01to{today}"]


@pytest.mark.asyncio
async def test_rejects_future_brave_llm_context_date_after_only_ranges_before_fetch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("BRAVE_API_KEY", "test-key")
    calls = _install_brave_fetch(
        monkeypatch,
        lambda _params: _json_response({"grounding": {"generic": []}, "sources": []}),
    )
    provider = create_brave_web_search_provider()
    tool = provider["create_tool"](
        {
            "config": {},
            "search_config": {"apiKey": "BSA...", "brave": {"mode": "llm-context"}},
        }
    )
    assert tool is not None

    result = await tool["execute"]({"query": "latest ai news", "date_after": "2999-01-01"})

    assert result == {
        "error": "invalid_date_range",
        "message": "date_after cannot be in the future for Brave llm-context mode.",
        "docs": "https://docs.openclaw.ai/tools/web",
    }
    assert calls == []


@pytest.mark.asyncio
async def test_rejects_brave_llm_context_date_before_only_ranges_before_fetch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("BRAVE_API_KEY", "test-key")
    calls = _install_brave_fetch(
        monkeypatch,
        lambda _params: _json_response({"grounding": {"generic": []}, "sources": []}),
    )
    provider = create_brave_web_search_provider()
    tool = provider["create_tool"](
        {
            "config": {},
            "search_config": {"apiKey": "BSA...", "brave": {"mode": "llm-context"}},
        }
    )
    assert tool is not None

    result = await tool["execute"]({"query": "latest ai news", "date_before": "2025-01-31"})

    assert result == {
        "error": "unsupported_date_filter",
        "message": (
            "Brave llm-context mode requires date_after when date_before is set. "
            "Use a bounded date range or freshness."
        ),
        "docs": "https://docs.openclaw.ai/tools/web",
    }
    assert calls == []


@pytest.mark.asyncio
async def test_falls_back_unsupported_country_values_before_calling_brave(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("BRAVE_API_KEY", "test-key")
    calls = _install_brave_fetch(monkeypatch, lambda _params: _empty_web_search_response())
    provider = create_brave_web_search_provider()
    tool = provider["create_tool"](
        {
            "config": {},
            "search_config": {"apiKey": "BSA...", "brave": {"apiKey": "BSA..."}},
        }
    )
    assert tool is not None

    await tool["execute"]({"query": "latest Vietnam news", "country": "VN"})

    query = parse_qs(urlparse(_request_url(calls)).query)
    assert query["country"] == ["ALL"]


@pytest.mark.asyncio
async def test_emits_brave_http_diagnostics_for_requests_responses_and_cache_events(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = _install_brave_fetch(
        monkeypatch,
        lambda _params: _json_response(
            {
                "web": {
                    "results": [
                        {
                            "title": "Diagnostics",
                            "url": "https://example.com/diagnostics",
                            "description": "debug details",
                        }
                    ]
                }
            }
        ),
    )
    provider = create_brave_web_search_provider()
    tool = provider["create_tool"](
        {
            "config": {"diagnostics": {"flags": ["brave.http"]}},
            "search_config": {"apiKey": "brave-test-key", "brave": {"mode": "web"}},
        }
    )
    assert tool is not None

    await tool["execute"]({"query": "unique brave diagnostics query", "count": 1})
    await tool["execute"]({"query": "unique brave diagnostics query", "count": 1})

    assert len(calls) == 1
    messages = [f"brave http {event}" for event, _meta in runtime_module.brave_http_log_records]
    assert messages == [
        "brave http cache miss",
        "brave http request",
        "brave http response",
        "brave http cache write",
        "brave http cache hit",
    ]
    request_log = next(
        (meta for event, meta in runtime_module.brave_http_log_records if event == "request"),
        None,
    )
    assert request_log == {
        "mode": "web",
        "query": "unique brave diagnostics query",
        "params": {
            "count": "1",
            "q": "unique brave diagnostics query",
        },
        "url": (
            "https://api.search.brave.com/res/v1/web/search?"
            "q=unique+brave+diagnostics+query&count=1"
        ),
    }
    response_log = next(
        (meta for event, meta in runtime_module.brave_http_log_records if event == "response"),
        None,
    )
    assert response_log is not None
    assert response_log["mode"] == "web"
    assert response_log["status"] == 200
    assert response_log["ok"] is True
    assert isinstance(response_log["durationMs"], int)
    assert response_log["durationMs"] >= 0
    serialized = json.dumps(runtime_module.brave_http_log_records)
    assert "brave-test-key" not in serialized
    assert "X-Subscription-Token" not in serialized
