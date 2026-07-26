"""Tests for Anthropic Vertex API stream factories."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from openclaw_extensions.anthropic_vertex.api import (
    create_anthropic_vertex_stream_fn,
    create_anthropic_vertex_stream_fn_for_model,
)


def _create_stream_deps() -> tuple[dict[str, Any], MagicMock, MagicMock]:
    stream_anthropic_mock = MagicMock(return_value=MagicMock())
    anthropic_vertex_ctor_mock = MagicMock()
    mock_anthropic_vertex = MagicMock(side_effect=anthropic_vertex_ctor_mock)

    return (
        {
            "AnthropicVertex": mock_anthropic_vertex,
            "streamAnthropic": stream_anthropic_mock,
        },
        stream_anthropic_mock,
        anthropic_vertex_ctor_mock,
    )


def _make_model() -> dict[str, Any]:
    return {
        "id": "claude-sonnet-4-6",
        "api": "anthropic-messages",
        "provider": "anthropic-vertex",
        "maxTokens": 128000,
    }


def test_reuses_runtime_stream_factory_across_direct_stream_calls() -> None:
    deps, stream_anthropic_mock, anthropic_vertex_ctor_mock = _create_stream_deps()
    stream_fn = create_anthropic_vertex_stream_fn("vertex-project", "us-east5", None, deps)
    model = _make_model()

    stream_fn(model, {"messages": []}, {})
    stream_fn(model, {"messages": []}, {})

    assert anthropic_vertex_ctor_mock.call_count == 1
    assert stream_anthropic_mock.call_count == 2


def test_reuses_runtime_stream_factory_across_model_derived_stream_calls() -> None:
    deps, stream_anthropic_mock, anthropic_vertex_ctor_mock = _create_stream_deps()
    stream_fn = create_anthropic_vertex_stream_fn_for_model(
        _make_model(),
        {
            "ANTHROPIC_VERTEX_PROJECT_ID": "vertex-project",
            "GOOGLE_CLOUD_LOCATION": "us-east5",
        },
        deps,
    )
    model = _make_model()

    stream_fn(model, {"messages": []}, {})
    stream_fn(model, {"messages": []}, {})

    assert anthropic_vertex_ctor_mock.call_count == 1
    assert stream_anthropic_mock.call_count == 2
