"""Tests for @openclaw/llm-runtime API registry."""

from __future__ import annotations

import pytest

from openclaw.llm.core import Model
from openclaw.llm.event_stream import create_assistant_message_event_stream
from openclaw_packages.llm_runtime import (
    get_api_provider,
    register_api_provider,
    unregister_api_providers,
)

TEST_SOURCE_ID = "test:llm-runtime-api-registry"

model = Model(
    id="test-model",
    name="Test Model",
    api="test-api",
    provider="test-provider",
    baseUrl="https://example.invalid",
    input=["text"],
    reasoning=False,
    contextWindow=1000,
    maxTokens=100,
)


@pytest.fixture(autouse=True)
def _cleanup_registry() -> None:
    yield
    unregister_api_providers(TEST_SOURCE_ID)


def test_rejects_mismatched_model_api_calls() -> None:
    register_api_provider(
        {
            "api": "test-api",
            "stream": lambda *_args, **_kwargs: create_assistant_message_event_stream(),
            "stream_simple": lambda *_args, **_kwargs: create_assistant_message_event_stream(),
        },
        TEST_SOURCE_ID,
    )

    provider = get_api_provider("test-api")
    assert provider is not None
    with pytest.raises(ValueError, match="Mismatched api: other-api expected test-api"):
        provider["stream_simple"](model.model_copy(update={"api": "other-api"}), {"messages": []})
