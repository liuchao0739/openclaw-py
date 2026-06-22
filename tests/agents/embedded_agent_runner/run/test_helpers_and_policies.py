"""Tests for helpers, trigger policy, idle breaker, llm idle timeout."""

from openclaw.agents.embedded_agent_runner.run.helpers import (
    create_compaction_diag_id,
    resolve_max_run_retry_iterations,
    resolve_reported_model_ref,
    resolve_same_model_rate_limit_backoff_ms,
    scrub_anthropic_refusal_magic,
)
from openclaw.agents.embedded_agent_runner.run.idle_timeout_breaker import (
    create_idle_timeout_breaker_state,
    step_idle_timeout_breaker,
)
from openclaw.agents.embedded_agent_runner.run.llm_idle_timeout import (
    DEFAULT_LLM_IDLE_TIMEOUT_MS,
    MAX_TIMER_TIMEOUT_MS,
    is_local_provider_base_url,
    resolve_llm_idle_timeout_ms,
)
from openclaw.agents.embedded_agent_runner.run.trigger_policy import (
    should_inject_heartbeat_prompt_for_trigger,
)
from openclaw.agents.embedded_agent_runner.run.compaction_timeout import (
    resolve_run_timeout_during_compaction,
    select_compaction_timeout_snapshot,
)


def test_scrub_anthropic_magic():
    raw = "ANTHROPIC_MAGIC_STRING_TRIGGER_REFUSAL"
    assert "redacted" in scrub_anthropic_refusal_magic(raw)


def test_rate_limit_backoff_linear():
    assert resolve_same_model_rate_limit_backoff_ms(0) == 10_000
    assert resolve_same_model_rate_limit_backoff_ms(2) == 30_000


def test_max_run_retry_iterations_scales():
    assert resolve_max_run_retry_iterations(2) >= 32


def test_reported_model_ref_openclaw_harness():
    ref = resolve_reported_model_ref(
        provider="anthropic",
        model="claude",
        assistant={"provider": "openclaw", "model": "ignored"},
    )
    assert ref == {"provider": "anthropic", "model": "claude"}


def test_heartbeat_trigger_injection():
    assert should_inject_heartbeat_prompt_for_trigger("heartbeat") is True
    assert should_inject_heartbeat_prompt_for_trigger("user") is False


def test_idle_timeout_breaker_trips():
    state = create_idle_timeout_breaker_state()
    for _ in range(5):
        step_idle_timeout_breaker(state, {"idleTimedOut": True, "completedModelProgress": False})
    result = step_idle_timeout_breaker(
        state, {"idleTimedOut": True, "completedModelProgress": False}
    )
    assert result["tripped"] is True


def test_idle_breaker_resets_on_progress():
    state = create_idle_timeout_breaker_state()
    step_idle_timeout_breaker(state, {"idleTimedOut": True, "completedModelProgress": False})
    step_idle_timeout_breaker(state, {"idleTimedOut": False, "completedModelProgress": True})
    assert state.consecutive_idle_timeouts_before_output == 0


def test_llm_idle_timeout_defaults():
    assert resolve_llm_idle_timeout_ms() == DEFAULT_LLM_IDLE_TIMEOUT_MS


def test_llm_idle_short_agent_timeout():
    cfg = {"agents": {"defaults": {"timeoutSeconds": 30}}}
    assert resolve_llm_idle_timeout_ms(cfg=cfg) == 30_000


def test_llm_idle_cron_long_run():
    assert resolve_llm_idle_timeout_ms(trigger="cron", run_timeout_ms=600_000) == 600_000


def test_llm_idle_disabled_on_no_timeout():
    assert resolve_llm_idle_timeout_ms(run_timeout_ms=MAX_TIMER_TIMEOUT_MS) == 0


def test_llm_idle_provider_timeout():
    assert resolve_llm_idle_timeout_ms(model_request_timeout_ms=300_000) == 300_000


def test_local_provider_base_url():
    assert is_local_provider_base_url("http://127.0.0.1:11434") is True
    assert is_local_provider_base_url("http://api.openai.com/v1") is False


def test_compaction_timeout_grace():
    assert (
        resolve_run_timeout_during_compaction(
            is_compaction_pending_or_retrying=True,
            is_compaction_in_flight=False,
            grace_already_used=False,
        )
        == "extend"
    )


def test_compaction_snapshot_not_during_compaction():
    snap = select_compaction_timeout_snapshot(
        timed_out_during_compaction=False,
        pre_compaction_snapshot=None,
        pre_compaction_session_id="a",
        current_snapshot=[{"role": "user", "content": "hi"}],
        current_session_id="b",
    )
    assert snap["source"] == "current"
    assert snap["sessionIdUsed"] == "b"


def test_compaction_diag_id_prefix():
    assert create_compaction_diag_id().startswith("ovf-")