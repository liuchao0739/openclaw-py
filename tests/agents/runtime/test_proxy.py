"""Tests for runtime proxy event processing (P2-0013)."""

from openclaw.agents.runtime.proxy import (
    build_proxy_request_options,
    process_proxy_event,
    sanitize_proxy_model,
)


def test_sanitize_proxy_model_strips_headers():
    model = {"id": "m", "headers": {"Authorization": "secret"}}
    assert "headers" not in sanitize_proxy_model(model)


def test_build_proxy_request_options():
    opts = build_proxy_request_options(
        {"temperature": 0.5, "authToken": "x", "promptCacheKey": "k"}
    )
    assert opts == {"temperature": 0.5, "promptCacheKey": "k"}
    assert "authToken" not in opts


def test_process_proxy_text_and_done():
    partial = {
        "role": "assistant",
        "content": [],
        "stopReason": "stop",
        "usage": {},
    }
    assert process_proxy_event({"type": "start"}, partial)["type"] == "start"
    process_proxy_event({"type": "text_start", "contentIndex": 0}, partial)
    process_proxy_event(
        {"type": "text_delta", "contentIndex": 0, "delta": "hi"}, partial
    )
    end = process_proxy_event({"type": "text_end", "contentIndex": 0}, partial)
    assert end["content"] == "hi"
    done = process_proxy_event(
        {"type": "done", "reason": "stop", "usage": {"input": 1}}, partial
    )
    assert done["type"] == "done"
    assert partial["usage"]["input"] == 1