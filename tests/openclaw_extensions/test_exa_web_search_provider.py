"""Tests for the exa web search provider."""

from __future__ import annotations

import json
import math
from datetime import datetime
from typing import Any

import httpx
import pytest

from openclaw_extensions.exa.src.exa_web_search_provider import create_exa_web_search_provider
from openclaw_extensions.exa.src.exa_web_search_provider_runtime import testing
from openclaw_extensions.exa.web_search_contract_api import (
    create_exa_web_search_provider as create_contract_exa_web_search_provider,
)


class _StreamReader:
    def __init__(self, chunk_count: int, chunk_size: int, *, text: str = "a") -> None:
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
    def __init__(self, reader: _StreamReader) -> None:
        self.body = _StreamingBody(reader)
        self._reader = reader

    async def text(self) -> str:
        raise RuntimeError("unbounded")

    async def aread(self) -> bytes:
        raise RuntimeError("unbounded")


def _create_streaming_json_response(
    *,
    chunk_count: int,
    chunk_size: int,
) -> dict[str, Any]:
    reader = _StreamReader(chunk_count, chunk_size)
    return {
        "response": _StreamingResponse(reader),
        "get_read_count": lambda: reader._reads,
    }


def _create_tracked_response(text: str, *, status: int = 503) -> dict[str, Any]:
    reader = _StreamReader(1, len(text), text=text)
    response = _StreamingResponse(reader)
    response.status_code = status
    return {
        "response": response,
        "was_canceled": lambda: reader._canceled,
    }


@pytest.fixture(autouse=True)
def reset_exa_runtime_module(monkeypatch: pytest.MonkeyPatch) -> None:
    import openclaw_extensions.exa.src.exa_web_search_provider as provider_module

    monkeypatch.setattr(provider_module, "_exa_runtime_module", None)


def test_exposes_expected_metadata_and_selection_wiring() -> None:
    provider = create_exa_web_search_provider()
    apply_selection_config = provider.get("apply_selection_config")
    assert apply_selection_config is not None

    applied = apply_selection_config({})

    assert provider["id"] == "exa"
    assert provider["onboarding_scopes"] == ["text-inference"]
    assert provider["credential_path"] == "plugins.entries.exa.config.webSearch.apiKey"
    plugin_entry = applied.get("plugins", {}).get("entries", {}).get("exa")
    assert plugin_entry is not None
    assert plugin_entry["enabled"] is True


def test_keeps_contract_surface_aligned_with_provider_metadata() -> None:
    provider = create_exa_web_search_provider()
    contract_provider = create_contract_exa_web_search_provider()
    apply_selection_config = contract_provider.get("apply_selection_config")
    assert apply_selection_config is not None
    applied = apply_selection_config({})

    assert {
        "id": contract_provider["id"],
        "label": contract_provider["label"],
        "hint": contract_provider["hint"],
        "onboarding_scopes": contract_provider["onboarding_scopes"],
        "credential_label": contract_provider["credential_label"],
        "env_vars": contract_provider["env_vars"],
        "placeholder": contract_provider["placeholder"],
        "signup_url": contract_provider["signup_url"],
        "docs_url": contract_provider["docs_url"],
        "auto_detect_order": contract_provider["auto_detect_order"],
        "credential_path": contract_provider["credential_path"],
    } == {
        "id": provider["id"],
        "label": provider["label"],
        "hint": provider["hint"],
        "onboarding_scopes": provider["onboarding_scopes"],
        "credential_label": provider["credential_label"],
        "env_vars": provider["env_vars"],
        "placeholder": provider["placeholder"],
        "signup_url": provider["signup_url"],
        "docs_url": provider["docs_url"],
        "auto_detect_order": provider["auto_detect_order"],
        "credential_path": provider["credential_path"],
    }
    assert contract_provider["create_tool"]({"config": {}, "search_config": {}}) is None
    plugin_entry = applied.get("plugins", {}).get("entries", {}).get("exa")
    assert plugin_entry is not None
    assert plugin_entry["enabled"] is True


def test_prefers_scoped_configured_api_keys_over_environment_fallbacks() -> None:
    assert testing["resolve_exa_api_key"]({"apiKey": "exa-secret"}) == "exa-secret"


def test_resolves_exa_search_base_url_overrides() -> None:
    assert testing["resolve_exa_search_endpoint"]() == {"endpoint": "https://api.exa.ai/search"}
    assert testing["resolve_exa_search_endpoint"]({"baseUrl": "https://proxy.example/exa"}) == {
        "endpoint": "https://proxy.example/exa/search"
    }
    assert testing["resolve_exa_search_endpoint"]({"baseUrl": "proxy.example/exa/search/"}) == {
        "endpoint": "https://proxy.example/exa/search"
    }
    assert testing["resolve_exa_search_endpoint"]({"baseUrl": "ftp://proxy.example/exa"}) == {
        "docs": "https://docs.openclaw.ai/tools/exa-search",
        "error": "invalid_base_url",
        "message": (
            "plugins.entries.exa.config.webSearch.baseUrl must be a valid http(s) URL. "
            "Got: ftp://proxy.example/exa"
        ),
    }


def test_partitions_exa_cache_keys_by_resolved_endpoint() -> None:
    base = {
        "type": "auto",
        "query": "openclaw",
        "count": 5,
    }
    assert testing["build_exa_cache_key"](
        {**base, "endpoint": "https://api.exa.ai/search"}
    ) != testing["build_exa_cache_key"]({**base, "endpoint": "https://proxy.example/exa/search"})


def test_normalizes_exa_result_descriptions_from_highlights_before_text() -> None:
    assert (
        testing["resolve_exa_description"](
            {"highlights": ["first", "", "second"], "text": "full text"}
        )
        == "first\nsecond"
    )
    assert testing["resolve_exa_description"]({"text": "full text"}) == "full text"


def test_handles_month_freshness_without_date_overflow() -> None:
    iso = testing["resolve_freshness_start_date"]("month")
    assert not math.isnan(datetime.fromisoformat(iso).timestamp())


def test_accepts_current_exa_contents_object_options_from_docs() -> None:
    assert testing["parse_exa_contents"](
        {
            "text": {"maxCharacters": 1200},
            "highlights": {
                "maxCharacters": 4000,
                "query": "latest model launches",
                "numSentences": 4,
                "highlightsPerUrl": 2,
            },
            "summary": {"query": "launch details"},
        }
    ) == {
        "value": {
            "text": {"maxCharacters": 1200},
            "highlights": {
                "maxCharacters": 4000,
                "query": "latest model launches",
                "numSentences": 4,
                "highlightsPerUrl": 2,
            },
            "summary": {"query": "launch details"},
        }
    }


def test_rejects_invalid_exa_contents_objects() -> None:
    assert testing["parse_exa_contents"]({"highlights": {"numSentences": 0}}) == {
        "error": "invalid_contents",
        "message": "contents.highlights.numSentences must be a positive integer.",
        "docs": "https://docs.openclaw.ai/tools/web",
    }


def test_exposes_documented_exa_search_types_and_count_limits() -> None:
    provider = create_exa_web_search_provider()
    tool = provider["create_tool"](
        {"config": {}, "search_config": {"exa": {"apiKey": "exa-secret"}}}
    )
    assert tool is not None

    parameters = tool["parameters"]
    properties = parameters["properties"]

    assert properties["count"]["maximum"] == 100
    assert properties["type"]["enum"] == [
        "auto",
        "neural",
        "fast",
        "deep",
        "deep-reasoning",
        "instant",
    ]
    assert testing["resolve_exa_search_count"](80, 10) == 80
    assert testing["resolve_exa_search_count"](120, 10) == 100
    assert testing["resolve_exa_search_count"]("+05", 10) == 5
    assert testing["resolve_exa_search_count"]("0x10", 10) == 10
    assert testing["resolve_exa_search_count"]("1e2", 10) == 10
    assert testing["resolve_exa_search_count"](1.5, 10) == 10


@pytest.mark.asyncio
async def test_returns_validation_errors_for_conflicting_time_filters() -> None:
    provider = create_exa_web_search_provider()
    tool = provider["create_tool"](
        {"config": {}, "search_config": {"exa": {"apiKey": "exa-secret"}}}
    )
    assert tool is not None

    result = await tool["execute"](
        {
            "query": "latest gpu news",
            "freshness": "day",
            "date_after": "2026-03-01",
        }
    )

    assert result == {
        "error": "conflicting_time_filters",
        "message": (
            "freshness cannot be combined with date_after or date_before. Use one time-filter mode."
        ),
        "docs": "https://docs.openclaw.ai/tools/web",
    }


@pytest.mark.asyncio
async def test_returns_validation_errors_for_invalid_date_input() -> None:
    provider = create_exa_web_search_provider()
    tool = provider["create_tool"](
        {"config": {}, "search_config": {"exa": {"apiKey": "exa-secret"}}}
    )
    assert tool is not None

    result = await tool["execute"](
        {
            "query": "latest gpu news",
            "date_after": "2026-02-31",
        }
    )

    assert result == {
        "error": "invalid_date",
        "message": "date_after must be YYYY-MM-DD format.",
        "docs": "https://docs.openclaw.ai/tools/web",
    }


@pytest.mark.asyncio
async def test_reports_malformed_exa_api_json_with_stable_provider_error() -> None:
    with pytest.raises(RuntimeError, match="Exa API returned malformed JSON"):
        await testing["read_exa_search_results"](httpx.Response(200, content=b"{ nope"))


@pytest.mark.asyncio
async def test_parses_well_formed_exa_search_json_under_byte_cap() -> None:
    response = httpx.Response(
        200,
        content=json.dumps(
            {"results": [{"url": "https://example.com", "title": "Example"}]}
        ).encode("utf-8"),
        headers={"content-type": "application/json"},
    )

    assert await testing["read_exa_search_results"](response) == [
        {"url": "https://example.com", "title": "Example"}
    ]


@pytest.mark.asyncio
async def test_caps_oversized_exa_search_json_instead_of_buffering_whole_body() -> None:
    streamed = _create_streaming_json_response(chunk_count=64, chunk_size=1024)

    with pytest.raises(RuntimeError, match="Exa API response exceeds 4096 bytes"):
        await testing["read_exa_search_results"](streamed["response"], max_bytes=4096)

    assert streamed["get_read_count"]() < 64


@pytest.mark.asyncio
async def test_bounds_exa_api_error_bodies_without_using_response_text() -> None:
    tracked = _create_tracked_response(f"{'exa upstream unavailable ' * 1024}tail")

    detail = await testing["read_exa_error_detail"](tracked["response"])

    assert "exa upstream unavailable" in detail
    assert "tail" not in detail
    assert await testing["read_exa_error_detail"](httpx.Response(503, content=b"short")) == "short"
    assert tracked["was_canceled"]() is True
