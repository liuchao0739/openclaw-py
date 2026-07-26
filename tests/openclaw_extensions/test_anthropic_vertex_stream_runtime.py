"""Tests for Anthropic Vertex stream runtime."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from openclaw_extensions.anthropic_vertex.stream_runtime import (
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


def _make_model(
    *,
    model_id: str,
    max_tokens: int | None = None,
    params: dict[str, Any] | None = None,
    reasoning: bool | None = True,
    thinking_level_map: dict[str, Any] | None = None,
) -> dict[str, Any]:
    model: dict[str, Any] = {
        "id": model_id,
        "api": "anthropic-messages",
        "provider": "anthropic-vertex",
        "reasoning": reasoning if reasoning is not None else True,
    }
    if max_tokens is not None:
        model["maxTokens"] = max_tokens
    if params is not None:
        model["params"] = params
    if thinking_level_map is not None:
        model["thinkingLevelMap"] = thinking_level_map
    return model


def _stream_transport_options(stream_anthropic_mock: MagicMock) -> dict[str, Any]:
    call = stream_anthropic_mock.call_args
    assert call is not None
    options = call.args[2]
    assert isinstance(options, dict)
    return options


def _build_budgeted_transport_payload() -> dict[str, Any]:
    return {
        "system": [
            {"type": "text", "text": "Stable prefix", "cache_control": {"type": "ephemeral"}},
            {"type": "text", "text": "Dynamic suffix"},
        ],
        "tools": [
            {
                "name": "exec",
                "input_schema": {"type": "object"},
                "cache_control": {"type": "ephemeral"},
            }
        ],
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Hello", "cache_control": {"type": "ephemeral"}}
                ],
            },
            {
                "role": "assistant",
                "content": [{"type": "tool_use", "id": "t1", "name": "exec", "input": {}}],
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": "t1",
                        "content": [],
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
            },
        ],
    }


def _count_cache_control_markers(payload: Any) -> int:
    count = 0

    def visit(value: Any) -> None:
        nonlocal count
        if isinstance(value, list):
            for item in value:
                visit(item)
            return
        if not isinstance(value, dict):
            return
        if "cache_control" in value:
            count += 1
        visit(value.get("content"))

    if isinstance(payload, dict):
        visit(payload.get("system"))
        visit(payload.get("tools"))
        visit(payload.get("messages"))
    return count


def test_omits_project_id_when_adc_credentials_are_used_without_explicit_project() -> None:
    deps, _, anthropic_vertex_ctor_mock = _create_stream_deps()
    stream_fn = create_anthropic_vertex_stream_fn(None, "global", None, deps)
    stream_fn(_make_model(model_id="claude-sonnet-4-6", max_tokens=128000), {"messages": []}, {})
    anthropic_vertex_ctor_mock.assert_called_once_with({"region": "global"})


def test_passes_explicit_base_url_through_to_vertex_client() -> None:
    deps, _, anthropic_vertex_ctor_mock = _create_stream_deps()
    stream_fn = create_anthropic_vertex_stream_fn(
        "vertex-project",
        "us-east5",
        "https://proxy.example.test/vertex/v1",
        deps,
    )
    stream_fn(_make_model(model_id="claude-sonnet-4-6", max_tokens=128000), {"messages": []}, {})
    anthropic_vertex_ctor_mock.assert_called_once_with(
        {
            "projectId": "vertex-project",
            "region": "us-east5",
            "baseURL": "https://proxy.example.test/vertex/v1",
        }
    )


def test_defaults_max_tokens_to_model_limit() -> None:
    deps, stream_anthropic_mock, _ = _create_stream_deps()
    stream_fn = create_anthropic_vertex_stream_fn("vertex-project", "us-east5", None, deps)
    stream_fn(_make_model(model_id="claude-opus-4-6", max_tokens=128000), {"messages": []}, {})
    assert _stream_transport_options(stream_anthropic_mock)["maxTokens"] == 128000


def test_clamps_explicit_max_tokens_to_selected_model_limit() -> None:
    deps, stream_anthropic_mock, _ = _create_stream_deps()
    stream_fn = create_anthropic_vertex_stream_fn("vertex-project", "us-east5", None, deps)
    stream_fn(
        _make_model(model_id="claude-sonnet-4-6", max_tokens=128000),
        {"messages": []},
        {"maxTokens": 999999},
    )
    assert _stream_transport_options(stream_anthropic_mock)["maxTokens"] == 128000


@pytest.mark.parametrize(
    "model_id",
    ["claude-opus-4-8", "claude-opus-4-7", "claude-fable-5", "claude-mythos-5"],
)
def test_omits_unsupported_temperature(model_id: str) -> None:
    deps, stream_anthropic_mock, _ = _create_stream_deps()
    stream_fn = create_anthropic_vertex_stream_fn("vertex-project", "us-east5", None, deps)
    stream_fn(
        _make_model(model_id=model_id, max_tokens=128000),
        {"messages": []},
        {"temperature": 0.7},
    )
    assert "temperature" not in _stream_transport_options(stream_anthropic_mock)


def test_preserves_temperature_for_vertex_models_that_support_custom_sampling() -> None:
    deps, stream_anthropic_mock, _ = _create_stream_deps()
    stream_fn = create_anthropic_vertex_stream_fn("vertex-project", "us-east5", None, deps)
    stream_fn(
        _make_model(model_id="claude-sonnet-4-6", max_tokens=128000),
        {"messages": []},
        {"temperature": 0.7},
    )
    assert _stream_transport_options(stream_anthropic_mock)["temperature"] == 0.7


def test_uses_fable_5_always_adaptive_vertex_contract() -> None:
    deps, stream_anthropic_mock, _ = _create_stream_deps()
    stream_fn = create_anthropic_vertex_stream_fn("vertex-project", "us-east5", None, deps)
    stream_fn(
        _make_model(model_id="claude-fable-5", max_tokens=128000),
        {"messages": []},
        {"temperature": 0.7},
    )
    options = _stream_transport_options(stream_anthropic_mock)
    assert options["thinkingEnabled"] is True
    assert options["effort"] == "high"
    assert options["maxTokens"] == 128000
    assert "temperature" not in options


def test_uses_mythos_5_mandatory_adaptive_vertex_contract_by_default() -> None:
    deps, stream_anthropic_mock, _ = _create_stream_deps()
    stream_fn = create_anthropic_vertex_stream_fn("vertex-project", "us-east5", None, deps)
    stream_fn(
        _make_model(model_id="claude-mythos-5", max_tokens=128000),
        {"messages": []},
        {"temperature": 0.7},
    )
    options = _stream_transport_options(stream_anthropic_mock)
    assert options["thinkingEnabled"] is True
    assert options["effort"] == "high"
    assert options["maxTokens"] == 128000
    assert "temperature" not in options


def test_uses_canonical_claude_policy_for_vertex_deployment_aliases() -> None:
    deps, stream_anthropic_mock, _ = _create_stream_deps()
    stream_fn = create_anthropic_vertex_stream_fn("vertex-project", "us-east5", None, deps)
    stream_fn(
        _make_model(
            model_id="production-claude",
            max_tokens=128000,
            params={"canonicalModelId": "claude-opus-4-8"},
        ),
        {"messages": []},
        {"reasoning": "xhigh", "temperature": 0.7},
    )
    options = _stream_transport_options(stream_anthropic_mock)
    assert options["thinkingEnabled"] is True
    assert options["effort"] == "xhigh"
    assert "temperature" not in options


def test_preserves_fable_5_low_effort_on_vertex() -> None:
    deps, stream_anthropic_mock, _ = _create_stream_deps()
    stream_fn = create_anthropic_vertex_stream_fn("vertex-project", "us-east5", None, deps)
    stream_fn(
        _make_model(model_id="claude-fable-5", max_tokens=128000),
        {"messages": []},
        {"reasoning": "low"},
    )
    options = _stream_transport_options(stream_anthropic_mock)
    assert options["thinkingEnabled"] is True
    assert options["effort"] == "low"


def test_preserves_fable_5_xhigh_effort_on_vertex() -> None:
    deps, stream_anthropic_mock, _ = _create_stream_deps()
    stream_fn = create_anthropic_vertex_stream_fn("vertex-project", "us-east5", None, deps)
    stream_fn(
        _make_model(model_id="claude-fable-5", max_tokens=128000),
        {"messages": []},
        {"reasoning": "xhigh"},
    )
    options = _stream_transport_options(stream_anthropic_mock)
    assert options["thinkingEnabled"] is True
    assert options["effort"] == "xhigh"


def test_maps_unsupported_xhigh_reasoning_to_high_effort_for_opus_4_6() -> None:
    deps, stream_anthropic_mock, _ = _create_stream_deps()
    stream_fn = create_anthropic_vertex_stream_fn("vertex-project", "us-east5", None, deps)
    stream_fn(
        _make_model(model_id="claude-opus-4-6", max_tokens=64000),
        {"messages": []},
        {"reasoning": "xhigh"},
    )
    options = _stream_transport_options(stream_anthropic_mock)
    assert options["thinkingEnabled"] is True
    assert options["effort"] == "high"


def test_maps_xhigh_reasoning_to_xhigh_effort_for_opus_4_8() -> None:
    deps, stream_anthropic_mock, _ = _create_stream_deps()
    stream_fn = create_anthropic_vertex_stream_fn("vertex-project", "us-east5", None, deps)
    stream_fn(
        _make_model(model_id="claude-opus-4-8", max_tokens=128000),
        {"messages": []},
        {"reasoning": "xhigh"},
    )
    options = _stream_transport_options(stream_anthropic_mock)
    assert options["thinkingEnabled"] is True
    assert options["effort"] == "xhigh"


def test_preserves_max_reasoning_for_opus_4_8() -> None:
    deps, stream_anthropic_mock, _ = _create_stream_deps()
    stream_fn = create_anthropic_vertex_stream_fn("vertex-project", "us-east5", None, deps)
    stream_fn(
        _make_model(model_id="claude-opus-4-8", max_tokens=128000),
        {"messages": []},
        {"reasoning": "max"},
    )
    options = _stream_transport_options(stream_anthropic_mock)
    assert options["thinkingEnabled"] is True
    assert options["effort"] == "max"


def test_preserves_native_max_reasoning_for_sonnet_4_6() -> None:
    deps, stream_anthropic_mock, _ = _create_stream_deps()
    stream_fn = create_anthropic_vertex_stream_fn("vertex-project", "us-east5", None, deps)
    stream_fn(
        _make_model(model_id="claude-sonnet-4-6", max_tokens=128000),
        {"messages": []},
        {"reasoning": "max"},
    )
    options = _stream_transport_options(stream_anthropic_mock)
    assert options["thinkingEnabled"] is True
    assert options["effort"] == "max"


def test_honors_explicit_max_opt_outs_for_vertex_aliases() -> None:
    deps, stream_anthropic_mock, _ = _create_stream_deps()
    stream_fn = create_anthropic_vertex_stream_fn("vertex-project", "us-east5", None, deps)
    stream_fn(
        _make_model(
            model_id="production-claude",
            params={"canonicalModelId": "claude-sonnet-4-6"},
            reasoning=False,
            thinking_level_map={"xhigh": None, "max": None},
        ),
        {"messages": []},
        {"reasoning": "max", "temperature": 0.2},
    )
    options = _stream_transport_options(stream_anthropic_mock)
    assert options["effort"] == "high"
    assert "temperature" not in options


def test_keeps_already_budgeted_cache_control_markers_intact_when_forwarding_payload_hooks() -> (
    None
):
    deps, stream_anthropic_mock, _ = _create_stream_deps()
    on_payload = MagicMock(side_effect=lambda payload, _model: payload)
    stream_fn = create_anthropic_vertex_stream_fn("vertex-project", "us-east5", None, deps)
    model = _make_model(model_id="claude-sonnet-4-6", max_tokens=64000)
    stream_fn(
        model,
        {"messages": [{"role": "user", "content": "Hello"}]},
        {"cacheRetention": "short", "onPayload": on_payload},
    )
    transport_options = _stream_transport_options(stream_anthropic_mock)
    transport_payload_hook = transport_options.get("onPayload")
    payload = _build_budgeted_transport_payload()
    next_payload = transport_payload_hook(payload, model)
    on_payload.assert_called_once_with(payload, model)
    assert _count_cache_control_markers(next_payload) == 4
    assert next_payload["system"][1] == {"type": "text", "text": "Dynamic suffix"}


def test_omits_transport_payload_hook_when_caller_provides_none() -> None:
    deps, stream_anthropic_mock, _ = _create_stream_deps()
    stream_fn = create_anthropic_vertex_stream_fn("vertex-project", "us-east5", None, deps)
    stream_fn(
        _make_model(model_id="claude-sonnet-4-6", max_tokens=64000),
        {"messages": [{"role": "user", "content": "Hello"}]},
        {"cacheRetention": "short"},
    )
    assert _stream_transport_options(stream_anthropic_mock).get("onPayload") is None


def test_omits_max_tokens_when_neither_model_nor_request_provide_finite_limit() -> None:
    deps, stream_anthropic_mock, _ = _create_stream_deps()
    stream_fn = create_anthropic_vertex_stream_fn("vertex-project", "us-east5", None, deps)
    model = _make_model(model_id="claude-sonnet-4-6")
    stream_fn(model, {"messages": []}, {"maxTokens": float("nan")})
    call = stream_anthropic_mock.call_args
    assert call is not None
    assert call.args[0] == model
    assert call.args[1] == {"messages": []}
    assert isinstance(call.args[2], dict)
    assert "maxTokens" not in call.args[2]


def test_derives_project_and_region_from_model_and_env() -> None:
    deps, _, anthropic_vertex_ctor_mock = _create_stream_deps()
    stream_fn = create_anthropic_vertex_stream_fn_for_model(
        {"baseUrl": "https://europe-west4-aiplatform.googleapis.com"},
        {"GOOGLE_CLOUD_PROJECT_ID": "vertex-project"},
        deps,
    )
    stream_fn(_make_model(model_id="claude-sonnet-4-6", max_tokens=64000), {"messages": []}, {})
    anthropic_vertex_ctor_mock.assert_called_once_with(
        {
            "projectId": "vertex-project",
            "region": "europe-west4",
            "baseURL": "https://europe-west4-aiplatform.googleapis.com/v1",
        }
    )


def test_preserves_explicit_custom_provider_base_urls() -> None:
    deps, _, anthropic_vertex_ctor_mock = _create_stream_deps()
    stream_fn = create_anthropic_vertex_stream_fn_for_model(
        {"baseUrl": "https://proxy.example.test/custom-root/v1"},
        {"GOOGLE_CLOUD_PROJECT_ID": "vertex-project"},
        deps,
    )
    stream_fn(_make_model(model_id="claude-sonnet-4-6", max_tokens=64000), {"messages": []}, {})
    anthropic_vertex_ctor_mock.assert_called_once_with(
        {
            "projectId": "vertex-project",
            "region": "global",
            "baseURL": "https://proxy.example.test/custom-root/v1",
        }
    )


def test_adds_v1_for_path_prefixed_custom_provider_base_urls() -> None:
    deps, _, anthropic_vertex_ctor_mock = _create_stream_deps()
    stream_fn = create_anthropic_vertex_stream_fn_for_model(
        {"baseUrl": "https://proxy.example.test/custom-root"},
        {"GOOGLE_CLOUD_PROJECT_ID": "vertex-project"},
        deps,
    )
    stream_fn(_make_model(model_id="claude-sonnet-4-6", max_tokens=64000), {"messages": []}, {})
    anthropic_vertex_ctor_mock.assert_called_once_with(
        {
            "projectId": "vertex-project",
            "region": "global",
            "baseURL": "https://proxy.example.test/custom-root/v1",
        }
    )
