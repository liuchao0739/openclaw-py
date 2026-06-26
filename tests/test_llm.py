"""Tests for LLM modules."""

from openclaw.llm.providers.stream_wrappers.reasoning_effort_utils import (
    map_thinking_level_to_reasoning_effort,
)
from openclaw.llm.providers.stream_wrappers.stream_payload_utils import (
    stream_with_payload_patch,
)


class TestReasoningEffort:
    def test_off(self):
        assert map_thinking_level_to_reasoning_effort("off") == "none"

    def test_adaptive(self):
        assert map_thinking_level_to_reasoning_effort("adaptive") == "medium"

    def test_max(self):
        assert map_thinking_level_to_reasoning_effort("max") == "xhigh"

    def test_passthrough(self):
        assert map_thinking_level_to_reasoning_effort("low") == "low"
        assert map_thinking_level_to_reasoning_effort("high") == "high"
        assert map_thinking_level_to_reasoning_effort("minimal") == "minimal"
        assert map_thinking_level_to_reasoning_effort("medium") == "medium"


class TestStreamWithPayloadPatch:
    def test_patches_payload(self):
        calls = []

        def underlying(model, context, options):
            on_payload = options["onPayload"]
            on_payload({"original": True})

        def patch(payload):
            payload["patched"] = True

        stream_with_payload_patch(underlying, "model", {}, None, patch)

    def test_calls_original_on_payload(self):
        original_calls = []

        def underlying(model, context, options):
            on_payload = options["onPayload"]
            on_payload({"data": 1}, "model")

        def original(payload, model):
            original_calls.append((payload, model))

        def patch(payload):
            pass

        stream_with_payload_patch(
            underlying, "model", {}, {"onPayload": original}, patch
        )
        assert len(original_calls) == 1

    def test_no_original_on_payload(self):
        def underlying(model, context, options):
            on_payload = options["onPayload"]
            on_payload({"data": 1})

        def patch(payload):
            payload["x"] = 1

        # should not raise
        stream_with_payload_patch(underlying, "m", {}, None, patch)

    def test_non_dict_payload_not_patched(self):
        def underlying(model, context, options):
            on_payload = options["onPayload"]
            on_payload("not a dict")

        patch_calls = []

        def patch(payload):
            patch_calls.append(payload)

        stream_with_payload_patch(underlying, "m", {}, None, patch)
        assert len(patch_calls) == 0
