"""Tests for the duckduckgo web search provider."""

from __future__ import annotations

from typing import Any

import pytest

from openclaw.agents.tools.common import ToolInputError
from openclaw_extensions.duckduckgo.src import ddg_client
from openclaw_extensions.duckduckgo.src.config import (
    DEFAULT_DDG_SAFE_SEARCH,
    resolve_ddg_region,
    resolve_ddg_safe_search,
)
from openclaw_extensions.duckduckgo.src.ddg_search_provider import (
    create_duck_duck_go_web_search_provider,
)
from openclaw_extensions.duckduckgo.web_search_contract_api import (
    create_duck_duck_go_web_search_provider as create_duck_duck_go_web_search_contract_provider,
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
    def __init__(self, reader: _StreamReader) -> None:
        self.body = _StreamingBody(reader)
        self._reader = reader

    async def text(self) -> str:
        raise RuntimeError("unbounded")

    async def aread(self) -> bytes:
        raise RuntimeError("unbounded")


def _create_streaming_response(
    *,
    chunk_count: int,
    chunk_size: int,
    text: str = "x",
) -> dict[str, Any]:
    reader = _StreamReader(chunk_count, chunk_size, text=text)
    return {
        "response": _StreamingResponse(reader),
        "get_read_count": lambda: reader._reads,
        "was_canceled": lambda: reader._canceled,
    }


@pytest.fixture(autouse=True)
def reset_ddg_client_module(monkeypatch: pytest.MonkeyPatch) -> None:
    import openclaw_extensions.duckduckgo.src.ddg_search_provider as provider_module

    monkeypatch.setattr(provider_module, "_ddg_client_module", None)


@pytest.fixture
def mock_run_duck_duck_go_search(monkeypatch: pytest.MonkeyPatch):
    calls: list[dict[str, Any]] = []

    async def run_duck_duck_go_search(params: dict[str, Any]) -> dict[str, Any]:
        calls.append(params)
        return params

    monkeypatch.setattr(ddg_client, "run_duck_duck_go_search", run_duck_duck_go_search)
    return calls


def test_exposes_keyless_metadata_and_enables_the_plugin_in_config() -> None:
    provider = create_duck_duck_go_web_search_provider()
    apply_selection_config = provider.get("apply_selection_config")
    assert apply_selection_config is not None

    applied = apply_selection_config({})

    assert provider["id"] == "duckduckgo"
    assert provider["label"] == "DuckDuckGo Search (experimental)"
    assert provider["onboarding_scopes"] == ["text-inference"]
    assert create_duck_duck_go_web_search_contract_provider()["onboarding_scopes"] == [
        "text-inference"
    ]
    assert provider["requires_credential"] is False
    assert provider["credential_path"] == ""
    plugin_entry = applied.get("plugins", {}).get("entries", {}).get("duckduckgo")
    assert plugin_entry is not None
    assert plugin_entry["enabled"] is True


@pytest.mark.asyncio
async def test_maps_generic_tool_arguments_into_duck_duck_go_search_params(
    mock_run_duck_duck_go_search: list[dict[str, Any]],
) -> None:
    provider = create_duck_duck_go_web_search_provider()
    tool = provider["create_tool"]({"config": {"test": True}})
    assert tool is not None

    result = await tool["execute"](
        {
            "query": "openclaw docs",
            "count": 4,
            "region": "us-en",
            "safeSearch": "off",
        }
    )

    assert mock_run_duck_duck_go_search == [
        {
            "config": {"test": True},
            "query": "openclaw docs",
            "count": 4,
            "region": "us-en",
            "safeSearch": "off",
        }
    ]
    assert result == mock_run_duck_duck_go_search[0]


@pytest.mark.asyncio
async def test_rejects_fractional_and_out_of_range_counts_before_searching(
    mock_run_duck_duck_go_search: list[dict[str, Any]],
) -> None:
    provider = create_duck_duck_go_web_search_provider()
    tool = provider["create_tool"]({"config": {"test": True}})
    assert tool is not None

    with pytest.raises(ToolInputError, match="count must be an integer from 1 to 10."):
        await tool["execute"]({"query": "openclaw docs", "count": 4.5})
    with pytest.raises(ToolInputError, match="count must be an integer from 1 to 10."):
        await tool["execute"]({"query": "openclaw docs", "count": 11})
    assert mock_run_duck_duck_go_search == []


@pytest.mark.asyncio
async def test_bounds_successful_duck_duck_go_html_bodies_without_using_response_text() -> None:
    streamed = _create_streaming_response(chunk_count=32, chunk_size=1024 * 1024, text="x")

    with pytest.raises(
        ValueError,
        match="DuckDuckGo search: text response exceeds 16777216 bytes",
    ):
        await ddg_client.testing["read_duck_duck_go_html_response"](streamed["response"])

    assert streamed["get_read_count"]() < 32
    assert streamed["was_canceled"]() is True


def test_reads_region_from_plugin_config_and_normalizes_empty_values_away() -> None:
    assert (
        resolve_ddg_region(
            {
                "plugins": {
                    "entries": {
                        "duckduckgo": {
                            "config": {
                                "webSearch": {
                                    "region": "de-de",
                                }
                            }
                        }
                    }
                }
            }
        )
        == "de-de"
    )
    assert (
        resolve_ddg_region(
            {
                "plugins": {
                    "entries": {
                        "duckduckgo": {
                            "config": {
                                "webSearch": {
                                    "region": "   ",
                                }
                            }
                        }
                    }
                }
            }
        )
        is None
    )


def test_defaults_safe_search_to_moderate_and_accepts_strict_and_off() -> None:
    assert resolve_ddg_safe_search(None) == DEFAULT_DDG_SAFE_SEARCH
    assert (
        resolve_ddg_safe_search(
            {
                "plugins": {
                    "entries": {
                        "duckduckgo": {
                            "config": {
                                "webSearch": {
                                    "safeSearch": "strict",
                                }
                            }
                        }
                    }
                }
            }
        )
        == "strict"
    )
    assert (
        resolve_ddg_safe_search(
            {
                "plugins": {
                    "entries": {
                        "duckduckgo": {
                            "config": {
                                "webSearch": {
                                    "safeSearch": "off",
                                }
                            }
                        }
                    }
                }
            }
        )
        == "off"
    )


def test_decodes_direct_and_redirect_urls_plus_common_html_entities() -> None:
    testing = ddg_client.testing
    assert (
        testing["decode_duck_duck_go_url"](
            "https://duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.com%2Fsearch%3Fq%3Dclaw"
        )
        == "https://example.com/search?q=claw"
    )
    assert testing["decode_duck_duck_go_url"]("https://example.com") == "https://example.com"
    assert (
        testing["decode_html_entities"]("Fish &amp; Chips&nbsp;&hellip; &#39;ok&#39;")
        == "Fish & Chips ... 'ok'"
    )


def test_does_not_double_decode_escaped_entities() -> None:
    testing = ddg_client.testing
    assert (
        testing["decode_html_entities"]("How to escape &amp;lt; in HTML")
        == "How to escape &lt; in HTML"
    )
    assert testing["decode_html_entities"]("a&amp;#39;b") == "a&#39;b"
    assert testing["decode_html_entities"]("a&#x26;amp;b") == "a&amp;b"


def test_parses_results_when_href_appears_before_class() -> None:
    html = """
      <a href="https://duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.com" class="result__a">
        Example &amp; Co
      </a>
      <a class="result__snippet">Fast&nbsp;search &hellip; with details</a>
      <a class="result__a" href="https://example.org/direct">Direct result</a>
      <a class="result__snippet">Second snippet</a>
    """
    assert ddg_client.testing["parse_duck_duck_go_html"](html) == [
        {
            "title": "Example & Co",
            "url": "https://example.com",
            "snippet": "Fast search ... with details",
        },
        {
            "title": "Direct result",
            "url": "https://example.org/direct",
            "snippet": "Second snippet",
        },
    ]


def test_detects_bot_challenge_pages_without_flagging_ordinary_result_snippets() -> None:
    challenge_html = """
      <html>
        <body>
          <form>
            <h1>Are you a human?</h1>
            <div class="g-recaptcha">captcha</div>
          </form>
        </body>
      </html>
    """
    normal_html = """
      <a class="result__a" href="https://example.com/challenge">Coding Challenge</a>
      <a class="result__snippet">A fun coding challenge for interview prep.</a>
    """
    testing = ddg_client.testing
    assert testing["is_bot_challenge"](challenge_html) is True
    assert testing["parse_duck_duck_go_html"](challenge_html) == []
    assert testing["is_bot_challenge"](normal_html) is False
    assert testing["parse_duck_duck_go_html"](normal_html) == [
        {
            "title": "Coding Challenge",
            "url": "https://example.com/challenge",
            "snippet": "A fun coding challenge for interview prep.",
        }
    ]
