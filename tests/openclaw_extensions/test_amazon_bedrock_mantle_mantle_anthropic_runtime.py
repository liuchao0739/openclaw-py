"""Tests for Amazon Bedrock Mantle Anthropic stream runtime."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from openclaw_extensions.amazon_bedrock_mantle.mantle_anthropic_runtime import (
    create_mantle_anthropic_stream_fn,
    resolve_mantle_anthropic_base_url,
)


def _create_test_model(**overrides: Any) -> dict[str, Any]:
    return {
        "id": "anthropic.claude-opus-4-7",
        "name": "Claude Opus 4.7",
        "provider": "amazon-bedrock-mantle",
        "api": "anthropic-messages",
        "baseUrl": "https://bedrock-mantle.us-east-1.api.aws/v1",
        "headers": {"X-Test": "model-header"},
        "reasoning": False,
        "input": ["text", "image"],
        "cost": {"input": 5, "output": 25, "cacheRead": 0.5, "cacheWrite": 6.25},
        "contextWindow": 1_000_000,
        "maxTokens": 128_000,
        **overrides,
    }


def _create_test_deps() -> dict[str, MagicMock]:
    return {
        "createClient": MagicMock(side_effect=lambda options: {"options": options}),
        "stream": MagicMock(),
    }


def _require_record(value: Any, label: str) -> dict[str, Any]:
    assert isinstance(value, dict), f"Expected {label} to be an object"
    return value


def _mock_call_arg(mock: MagicMock, index: int = 0, arg_index: int = 0) -> Any:
    return mock.call_args_list[index].args[arg_index]


def _expect_first_stream_call(
    deps: dict[str, MagicMock],
    model: dict[str, Any],
    context: Any,
) -> None:
    assert _mock_call_arg(deps["stream"], 0, 0) is model
    assert _mock_call_arg(deps["stream"], 0, 1) is context


def _first_stream_options(deps: dict[str, MagicMock]) -> dict[str, Any]:
    return _require_record(_mock_call_arg(deps["stream"], 0, 2), "stream options")


def test_create_mantle_anthropic_stream_fn_uses_auth_token_bearer_auth() -> None:
    stream = {"kind": "anthropic-stream"}
    model = _create_test_model()
    context = {"messages": []}
    deps = _create_test_deps()
    deps["stream"].return_value = stream

    result = create_mantle_anthropic_stream_fn(deps)(
        model,
        context,
        {
            "apiKey": "bedrock-bearer-token",
            "headers": {"X-Caller": "caller-header"},
        },
    )

    assert result is stream
    client_options = _require_record(_mock_call_arg(deps["createClient"]), "client options")
    assert client_options["apiKey"] is None
    assert client_options["authToken"] == "bedrock-bearer-token"
    assert client_options["baseURL"] == "https://bedrock-mantle.us-east-1.api.aws/anthropic"
    default_headers = _require_record(client_options["defaultHeaders"], "default headers")
    assert default_headers["accept"] == "application/json"
    assert default_headers["anthropic-beta"] == "fine-grained-tool-streaming-2025-05-14"
    assert default_headers["X-Test"] == "model-header"
    assert default_headers["X-Caller"] == "caller-header"

    _expect_first_stream_call(deps, model, context)
    stream_options = _first_stream_options(deps)
    client = _require_record(stream_options["client"], "stream client")
    assert _require_record(client["options"], "stream client options")["authToken"] == (
        "bedrock-bearer-token"
    )
    assert stream_options["thinkingEnabled"] is False


def test_create_mantle_anthropic_stream_fn_omits_opus_sampling_and_reasoning() -> None:
    model = _create_test_model()
    context = {"messages": []}
    deps = _create_test_deps()
    deps["stream"].return_value = {"kind": "anthropic-stream"}

    create_mantle_anthropic_stream_fn(deps)(
        model,
        context,
        {
            "apiKey": "bedrock-bearer-token",
            "temperature": 0.2,
            "reasoning": "high",
        },
    )

    _expect_first_stream_call(deps, model, context)
    stream_options = _first_stream_options(deps)
    assert stream_options["temperature"] is None
    assert stream_options["thinkingEnabled"] is False


def test_create_mantle_anthropic_stream_fn_defaults_mythos_to_high_effort() -> None:
    model = _create_test_model(
        id="anthropic.claude-mythos-preview",
        name="Claude Mythos Preview",
        reasoning=True,
        params={"canonicalModelId": "claude-mythos-preview"},
    )
    context = {"messages": []}
    deps = _create_test_deps()
    deps["stream"].return_value = {"kind": "anthropic-stream"}

    create_mantle_anthropic_stream_fn(deps)(
        model,
        context,
        {"apiKey": "bedrock-bearer-token"},
    )

    _expect_first_stream_call(deps, model, context)
    stream_options = _first_stream_options(deps)
    assert stream_options["thinkingEnabled"] is True
    assert stream_options["effort"] == "high"


def test_create_mantle_anthropic_stream_fn_clamps_mythos_max_effort_to_high() -> None:
    model = _create_test_model(
        id="anthropic.claude-mythos-preview",
        name="Claude Mythos Preview",
        reasoning=True,
        params={"canonicalModelId": "claude-mythos-preview"},
    )
    context = {"messages": []}
    deps = _create_test_deps()
    deps["stream"].return_value = {"kind": "anthropic-stream"}

    create_mantle_anthropic_stream_fn(deps)(
        model,
        context,
        {
            "apiKey": "bedrock-bearer-token",
            "reasoning": "max",
        },
    )

    _expect_first_stream_call(deps, model, context)
    stream_options = _first_stream_options(deps)
    assert stream_options["thinkingEnabled"] is True
    assert stream_options["effort"] == "high"


def test_create_mantle_anthropic_stream_fn_maps_mythos_minimal_to_low_effort() -> None:
    model = _create_test_model(
        id="anthropic.claude-mythos-preview",
        name="Claude Mythos Preview",
        reasoning=True,
        params={"canonicalModelId": "claude-mythos-preview"},
    )
    deps = _create_test_deps()
    deps["stream"].return_value = {"kind": "anthropic-stream"}

    create_mantle_anthropic_stream_fn(deps)(
        model,
        {"messages": []},
        {
            "apiKey": "bedrock-bearer-token",
            "reasoning": "minimal",
        },
    )

    stream_options = _first_stream_options(deps)
    assert stream_options["thinkingEnabled"] is True
    assert stream_options["effort"] == "low"


def test_resolve_mantle_anthropic_base_url() -> None:
    assert (
        resolve_mantle_anthropic_base_url("https://bedrock-mantle.us-east-1.api.aws/v1")
        == "https://bedrock-mantle.us-east-1.api.aws/anthropic"
    )
    assert (
        resolve_mantle_anthropic_base_url("https://bedrock-mantle.us-east-1.api.aws/anthropic/")
        == "https://bedrock-mantle.us-east-1.api.aws/anthropic"
    )
