"""Tests for incomplete turn classification (P2-0011)."""

from openclaw.agents.embedded_agent_runner.run.incomplete_turn import (
    build_attempt_replay_metadata,
    is_incomplete_terminal_assistant_turn,
    resolve_incomplete_turn_payload_text,
    resolve_run_liveness_state,
    should_retry_missing_assistant_turn,
)


def test_tool_use_stop_is_incomplete_even_with_visible_text():
    assert is_incomplete_terminal_assistant_turn(
        has_assistant_visible_text=True,
        last_assistant={"stopReason": "toolUse"},
    )
    assert is_incomplete_terminal_assistant_turn(
        has_assistant_visible_text=True,
        last_assistant={"stopReason": "length"},
    )
    assert not is_incomplete_terminal_assistant_turn(
        has_assistant_visible_text=True,
        has_terminal_output=True,
        last_assistant={"stopReason": "length"},
    )
    assert is_incomplete_terminal_assistant_turn(
        has_assistant_visible_text=True,
        has_terminal_output=True,
        last_assistant={"stopReason": "toolUse"},
    )


def test_replay_metadata_flags_messaging_delivery():
    meta = build_attempt_replay_metadata(
        tool_metas=[{"replaySafe": True}],
        did_send_via_messaging_tool=True,
    )
    assert meta["hadPotentialSideEffects"] is True
    assert meta["replaySafe"] is False


def test_incomplete_turn_warning_for_tool_only_output():
    attempt = {
        "assistantTexts": [],
        "toolMetas": [{"toolName": "bash"}],
        "messagesSnapshot": [],
    }
    text = resolve_incomplete_turn_payload_text(
        payload_count=0,
        aborted=False,
        external_abort=False,
        timed_out=False,
        attempt=attempt,
    )
    assert text is not None
    assert "couldn't generate a response" in text


def test_external_abort_suppresses_incomplete_warning():
    attempt = {"assistantTexts": [], "toolMetas": [{"toolName": "bash"}]}
    assert (
        resolve_incomplete_turn_payload_text(
            payload_count=0,
            aborted=True,
            external_abort=True,
            timed_out=False,
            attempt=attempt,
        )
        is None
    )


def test_liveness_abandoned_when_incomplete_text():
    attempt = {"assistantTexts": [], "lastAssistant": None}
    incomplete = "⚠️ Agent couldn't generate a response. Please try again."
    assert (
        resolve_run_liveness_state(
            payload_count=0,
            aborted=False,
            timed_out=False,
            attempt=attempt,
            incomplete_turn_text=incomplete,
        )
        == "abandoned"
    )


def test_should_retry_missing_assistant_when_replay_safe():
    attempt = {
        "assistantTexts": [],
        "toolMetas": [],
        "replayMetadata": {"hadPotentialSideEffects": False, "replaySafe": True},
    }
    assert should_retry_missing_assistant_turn(
        payload_count=0,
        aborted=False,
        timed_out=False,
        attempt=attempt,
    )