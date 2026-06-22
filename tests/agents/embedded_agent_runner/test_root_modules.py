"""Tests for embedded_agent_runner root modules (P2-0010)."""

from openclaw.agents.embedded_agent_runner.cache_ttl import (
    CACHE_TTL_CUSTOM_TYPE,
    is_cache_ttl_eligible_provider,
    read_last_cache_ttl_timestamp,
)
from openclaw.agents.embedded_agent_runner.compact_reasons import (
    classify_compaction_reason,
    resolve_compaction_failure_reason,
)
from openclaw.agents.embedded_agent_runner.delivery_evidence import (
    has_committed_outbound_delivery_evidence,
    has_outbound_delivery_evidence,
    has_visible_agent_payload,
)
from openclaw.agents.embedded_agent_runner.empty_assistant_turn import (
    is_zero_usage_empty_stop_assistant_turn,
)
from openclaw.agents.embedded_agent_runner.execution_phase import (
    format_embedded_agent_execution_phase,
)
from openclaw.agents.embedded_agent_runner.prompt_cache_retention import (
    is_google_prompt_cache_eligible,
)


def test_execution_phase_label():
    assert format_embedded_agent_execution_phase("model_call_started") == "model-call-started"


def test_compaction_reason_safeguard():
    assert (
        resolve_compaction_failure_reason(
            reason="Compaction cancelled",
            safeguard_cancel_reason="user stopped",
        )
        == "user stopped"
    )


def test_classify_compaction_timeout():
    assert classify_compaction_reason("compaction timed out") == "timeout"


def test_empty_assistant_turn():
    assert is_zero_usage_empty_stop_assistant_turn(
        {"stopReason": "stop", "content": [], "usage": {"total": 0, "input": 0, "output": 0}}
    )


def test_google_cache_eligible():
    assert is_google_prompt_cache_eligible(
        model_api="google-generative-ai", model_id="gemini-2.5-flash"
    )


def test_cache_ttl_anthropic():
    assert is_cache_ttl_eligible_provider("anthropic", "claude-sonnet-4")


def test_read_cache_ttl_timestamp():
    class SM:
        def get_entries(self):
            return [
                {
                    "type": "custom",
                    "customType": CACHE_TTL_CUSTOM_TYPE,
                    "data": {"timestamp": 12345, "provider": "anthropic"},
                }
            ]

    assert read_last_cache_ttl_timestamp(SM(), {"provider": "anthropic"}) == 12345


def test_visible_payload():
    assert has_visible_agent_payload({"payloads": [{"text": "hello"}]})


def test_outbound_evidence_messaging():
    assert has_outbound_delivery_evidence({"didSendViaMessagingTool": True})