"""Classifies incomplete terminal assistant turns and retry instructions."""

from __future__ import annotations

import re
from typing import Any, Literal, TypedDict

from openclaw.agents.accepted_session_spawn import has_accepted_session_spawn
from openclaw.agents.embedded_agent_runner.delivery_evidence import (
    has_committed_messaging_tool_delivery_evidence,
    has_messaging_tool_delivery_evidence,
)
from openclaw.agents.embedded_agent_runner.empty_assistant_turn import (
    is_zero_usage_empty_stop_assistant_turn,
)

EmbeddedRunLivenessState = Literal["working", "blocked", "paused", "abandoned"]

DEFAULT_REASONING_ONLY_RETRY_LIMIT = 2
DEFAULT_EMPTY_RESPONSE_RETRY_LIMIT = 1
REASONING_ONLY_RETRY_INSTRUCTION = (
    "The previous assistant turn recorded reasoning but did not produce a user-visible answer. "
    "Continue from that partial turn and produce the visible answer now. "
    "Do not restate the reasoning or restart from scratch."
)
EMPTY_RESPONSE_RETRY_INSTRUCTION = (
    "The previous attempt did not produce a user-visible answer. "
    "Continue from the current state and produce the visible answer now. "
    "Do not restart from scratch."
)

SILENT_REPLY_TOKEN = "[[SILENT]]"

GEMINI_INCOMPLETE_TURN_PROVIDER_IDS = frozenset(
    {"google", "google-vertex", "google-antigravity", "google-gemini-cli"}
)
GEMINI_INCOMPLETE_TURN_MODEL_ID_PATTERN = re.compile(r"^gemini(?:[.-]|$)", re.I)
OLLAMA_INCOMPLETE_TURN_PROVIDER_ID_PATTERN = re.compile(r"^ollama(?:-|$)", re.I)
RETRY_GUARD_MODEL_APIS = frozenset(
    {
        "openai-completions",
        "anthropic-messages",
        "bedrock-converse-stream",
        "openai-responses",
        "openai-chatgpt-responses",
        "azure-openai-responses",
        "openclaw-openai-responses-transport",
        "openclaw-azure-openai-responses-transport",
    }
)

REPLAY_UNSAFE_FALLBACK_METADATA: dict[str, Any] = {
    "hadPotentialSideEffects": True,
    "replaySafe": False,
}


class ReplayMetadata(TypedDict, total=False):
    hadPotentialSideEffects: bool
    replaySafe: bool


def _normalize_lower(value: object) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip().lower()


def _as_finite_number(value: object) -> float | None:
    if not isinstance(value, (int, float)) or value != value:
        return None
    return float(value)


def _has_positive_output_token_usage(message: dict[str, Any] | None) -> bool:
    if not message:
        return False
    usage = message.get("usage")
    if not isinstance(usage, dict):
        return False
    output = _as_finite_number(usage.get("output"))
    return output is not None and output > 0


def _collect_text_from_content(content: object) -> str:
    if isinstance(content, str):
        return content.strip()
    if not isinstance(content, list):
        return ""
    parts: list[str] = []
    for block in content:
        if isinstance(block, str) and block.strip():
            parts.append(block.strip())
        elif isinstance(block, dict):
            btype = block.get("type")
            if btype == "text" and isinstance(block.get("text"), str):
                text = block["text"].strip()
                if text:
                    parts.append(text)
    return "\n".join(parts)


def _has_only_assistant_reasoning_content(message: dict[str, Any] | None) -> bool:
    if not message or not isinstance(message.get("content"), list):
        return False
    content = message["content"]
    if not content:
        return False
    has_thinking = False
    for block in content:
        if isinstance(block, dict):
            btype = block.get("type")
            if btype in ("thinking", "redacted_thinking"):
                has_thinking = True
            elif btype == "text" and isinstance(block.get("text"), str) and block["text"].strip():
                return False
            elif btype in ("toolCall", "tool_use", "function_call"):
                return False
        elif isinstance(block, str) and block.strip():
            return False
    return has_thinking


def _assess_last_assistant_message(message: dict[str, Any]) -> str:
    """Minimal port of thinking.assessLastAssistantMessage recovery labels."""
    if not isinstance(message.get("content"), list):
        return "valid"
    content = message["content"]
    if not content:
        return "incomplete-thinking"
    text = _collect_text_from_content(content)
    if text:
        return "valid"
    if _has_only_assistant_reasoning_content(message):
        return "incomplete-text"
    return "incomplete-thinking"


def is_incomplete_terminal_assistant_turn(
    *,
    has_assistant_visible_text: bool,
    has_terminal_output: bool = False,
    last_assistant: dict[str, Any] | None = None,
) -> bool:
    stop_reason = last_assistant.get("stopReason") if last_assistant else None
    if stop_reason == "toolUse":
        return True
    if stop_reason == "length" and not has_terminal_output:
        return True
    return False


def build_attempt_replay_metadata(
    *,
    tool_metas: list[dict[str, Any]],
    did_send_via_messaging_tool: bool = False,
    messaging_tool_sent_texts: list[str] | None = None,
    messaging_tool_sent_media_urls: list[str] | None = None,
    messaging_tool_sent_targets: list[Any] | None = None,
    accepted_session_spawns: list[object] | None = None,
    successful_cron_adds: int = 0,
) -> ReplayMetadata:
    had_unsafe_tools = any(entry.get("replaySafe") is not True for entry in tool_metas)
    had_async_started = any(entry.get("asyncStarted") is True for entry in tool_metas)
    attempt_shape = {
        "didSendViaMessagingTool": did_send_via_messaging_tool,
        "messagingToolSentTexts": messaging_tool_sent_texts or [],
        "messagingToolSentMediaUrls": messaging_tool_sent_media_urls or [],
        "messagingToolSentTargets": messaging_tool_sent_targets or [],
    }
    had_potential = (
        had_unsafe_tools
        or had_async_started
        or has_messaging_tool_delivery_evidence(attempt_shape)
        or has_accepted_session_spawn(accepted_session_spawns)
        or successful_cron_adds > 0
    )
    return {
        "hadPotentialSideEffects": had_potential,
        "replaySafe": not had_potential,
    }


def resolve_attempt_replay_metadata(attempt: dict[str, Any]) -> ReplayMetadata:
    meta = attempt.get("replayMetadata")
    if isinstance(meta, dict) and "replaySafe" in meta:
        return meta  # type: ignore[return-value]
    return REPLAY_UNSAFE_FALLBACK_METADATA  # type: ignore[return-value]


def has_attempt_terminal_state(attempt: dict[str, Any]) -> bool:
    tool_media = attempt.get("toolMediaUrls")
    has_media = isinstance(tool_media, list) and any(
        isinstance(url, str) and url.strip() for url in tool_media
    )
    messaging = {
        "messagingToolSentTexts": attempt.get("messagingToolSentTexts") or [],
        "messagingToolSentMediaUrls": attempt.get("messagingToolSentMediaUrls") or [],
        "messagingToolSentTargets": attempt.get("messagingToolSentTargets") or [],
    }
    tool_metas = attempt.get("toolMetas")
    async_started = isinstance(tool_metas, list) and any(
        isinstance(t, dict) and t.get("asyncStarted") is True for t in tool_metas
    )
    source_payloads = attempt.get("messagingToolSourceReplyPayloads")
    return bool(
        attempt.get("clientToolCalls")
        or attempt.get("yieldDetected")
        or attempt.get("didSendDeterministicApprovalPrompt")
        or attempt.get("heartbeatToolResponse")
        or attempt.get("lastToolError")
        or has_media
        or attempt.get("toolAudioAsVoice")
        or attempt.get("toolTrustedLocalMedia")
        or attempt.get("hasToolMediaBlockReply")
        or attempt.get("didDeliverSourceReplyViaMessageTool")
        or (isinstance(source_payloads, list) and len(source_payloads) > 0)
        or has_committed_messaging_tool_delivery_evidence(messaging)
        or has_accepted_session_spawn(attempt.get("acceptedSessionSpawns"))
        or async_started
        or (isinstance(attempt.get("successfulCronAdds"), (int, float)) and attempt["successfulCronAdds"] > 0)
    )


def _join_assistant_texts(assistant_texts: list[str] | None) -> str:
    return "\n\n".join(assistant_texts or []).strip()


def _is_silent_reply_payload_text(text: str, token: str = SILENT_REPLY_TOKEN) -> bool:
    return text.strip() == token


def _has_only_silent_assistant_reply(assistant_texts: list[str] | None) -> bool:
    non_empty = [t for t in (assistant_texts or []) if isinstance(t, str) and t.strip()]
    return len(non_empty) > 0 and all(_is_silent_reply_payload_text(t) for t in non_empty)


def _has_async_started_tool_activity(tool_metas: list[dict[str, Any]] | None) -> bool:
    return any(isinstance(e, dict) and e.get("asyncStarted") is True for e in (tool_metas or []))


def resolve_incomplete_turn_payload_text(
    *,
    payload_count: int,
    aborted: bool,
    external_abort: bool,
    timed_out: bool,
    attempt: dict[str, Any],
) -> str | None:
    tool_use_terminal = (attempt.get("lastAssistant") or {}).get("stopReason") == "toolUse"
    assistant = attempt.get("currentAttemptAssistant") or attempt.get("lastAssistant")
    has_terminal_output = has_attempt_terminal_state(attempt)
    length_terminal = is_incomplete_terminal_assistant_turn(
        has_assistant_visible_text=payload_count > 0,
        has_terminal_output=has_terminal_output,
        last_assistant=assistant if isinstance(assistant, dict) else None,
    )
    thinking_only_terminal = (
        payload_count != 0
        and not _join_assistant_texts(attempt.get("assistantTexts"))
        and not has_terminal_output
        and isinstance(assistant, dict)
        and _has_only_assistant_reasoning_content(assistant)
    )

    if (
        (payload_count != 0 and not tool_use_terminal and not length_terminal and not thinking_only_terminal)
        or (aborted and external_abort)
        or timed_out
        or attempt.get("clientToolCalls")
        or attempt.get("yieldDetected")
        or attempt.get("didSendDeterministicApprovalPrompt")
        or attempt.get("lastToolError")
    ):
        return None

    if _has_only_silent_assistant_reply(attempt.get("assistantTexts")):
        return None

    if has_committed_messaging_tool_delivery_evidence(attempt):
        return None

    if has_accepted_session_spawn(attempt.get("acceptedSessionSpawns")):
        return None

    if _has_async_started_tool_activity(attempt.get("toolMetas")):
        return None

    last_assistant = attempt.get("lastAssistant")
    incomplete_terminal = is_incomplete_terminal_assistant_turn(
        has_assistant_visible_text=payload_count > 0,
        has_terminal_output=has_terminal_output,
        last_assistant=last_assistant if isinstance(last_assistant, dict) else None,
    )
    reasoning_only = (
        isinstance(assistant, dict) and _assess_last_assistant_message(assistant) == "incomplete-text"
    )
    empty_response = _is_empty_response_assistant_turn(payload_count=payload_count, attempt=attempt)
    stop_reason = (last_assistant or {}).get("stopReason") if isinstance(last_assistant, dict) else None

    if (
        not incomplete_terminal
        and not length_terminal
        and not reasoning_only
        and not thinking_only_terminal
        and not empty_response
        and stop_reason != "error"
    ):
        return None

    if resolve_attempt_replay_metadata(attempt).get("hadPotentialSideEffects"):
        return (
            "⚠️ Agent couldn't generate a response. Note: some tool actions may have already been "
            "executed — please verify before retrying."
        )
    return "⚠️ Agent couldn't generate a response. Please try again."


def should_retry_missing_assistant_turn(
    *,
    payload_count: int,
    aborted: bool,
    prompt_error: object = None,
    timed_out: bool,
    attempt: dict[str, Any],
) -> bool:
    if (
        payload_count != 0
        or aborted
        or prompt_error
        or timed_out
        or attempt.get("clientToolCalls")
        or attempt.get("currentAttemptAssistant")
        or attempt.get("lastAssistant")
        or attempt.get("yieldDetected")
        or attempt.get("didSendDeterministicApprovalPrompt")
        or attempt.get("lastToolError")
    ):
        return False

    if _has_only_silent_assistant_reply(attempt.get("assistantTexts")):
        return False

    if _join_assistant_texts(attempt.get("assistantTexts")):
        return False

    if has_committed_messaging_tool_delivery_evidence(attempt):
        return False

    if has_accepted_session_spawn(attempt.get("acceptedSessionSpawns")):
        return False

    if _has_async_started_tool_activity(attempt.get("toolMetas")):
        return False

    lifecycle = attempt.get("itemLifecycle")
    if isinstance(lifecycle, dict):
        if (lifecycle.get("startedCount") or 0) > 0 or (lifecycle.get("activeCount") or 0) > 0:
            return False

    return not resolve_attempt_replay_metadata(attempt).get("hadPotentialSideEffects")


def resolve_replay_invalid_flag(
    *,
    attempt: dict[str, Any],
    incomplete_turn_text: str | None = None,
) -> bool:
    return (
        not resolve_attempt_replay_metadata(attempt).get("replaySafe")
        or attempt.get("promptErrorSource") == "compaction"
        or attempt.get("timedOutDuringCompaction") is True
        or bool(incomplete_turn_text)
    )


def resolve_run_liveness_state(
    *,
    payload_count: int,
    aborted: bool,
    timed_out: bool,
    attempt: dict[str, Any],
    incomplete_turn_text: str | None = None,
) -> EmbeddedRunLivenessState:
    if incomplete_turn_text:
        return "abandoned"
    if attempt.get("promptErrorSource") == "compaction" or attempt.get("timedOutDuringCompaction"):
        return "paused"
    if (aborted or timed_out) and payload_count == 0:
        return "blocked"
    last = attempt.get("lastAssistant")
    if isinstance(last, dict) and last.get("stopReason") == "error":
        return "blocked"
    return "working"


def _is_empty_response_assistant_turn(*, payload_count: int, attempt: dict[str, Any]) -> bool:
    if payload_count != 0:
        return False
    if _join_assistant_texts(attempt.get("assistantTexts")):
        return False
    assistant = attempt.get("currentAttemptAssistant") or attempt.get("lastAssistant")
    if not assistant:
        return True
    if not isinstance(assistant, dict):
        return False
    if assistant.get("stopReason") == "error":
        return False
    if is_incomplete_terminal_assistant_turn(
        has_assistant_visible_text=False,
        last_assistant=assistant,
    ):
        return False
    if _assess_last_assistant_message(assistant) == "incomplete-text":
        return False
    return True


def _should_apply_non_visible_turn_retry_guard(
    *,
    provider: str | None = None,
    model_id: str | None = None,
    model_api: str | None = None,
    execution_contract: str | None = None,
) -> bool:
    if execution_contract == "strict-agentic":
        return True
    provider_norm = _normalize_lower(provider)
    model = model_id or ""
    if provider_norm in GEMINI_INCOMPLETE_TURN_PROVIDER_IDS and GEMINI_INCOMPLETE_TURN_MODEL_ID_PATTERN.match(
        model.split("/")[-1] if "/" in model else model
    ):
        return True
    if _normalize_lower(model_api) in RETRY_GUARD_MODEL_APIS:
        return True
    return bool(OLLAMA_INCOMPLETE_TURN_PROVIDER_ID_PATTERN.match(provider_norm))


def resolve_empty_response_retry_instruction(
    *,
    provider: str | None = None,
    model_id: str | None = None,
    model_api: str | None = None,
    execution_contract: str | None = None,
    payload_count: int,
    aborted: bool,
    timed_out: bool,
    attempt: dict[str, Any],
) -> str | None:
    if aborted or timed_out or attempt.get("clientToolCalls") or attempt.get("yieldDetected"):
        return None
    if attempt.get("didSendDeterministicApprovalPrompt") or attempt.get("lastToolError"):
        return None
    if has_accepted_session_spawn(attempt.get("acceptedSessionSpawns")):
        return None
    if resolve_attempt_replay_metadata(attempt).get("hadPotentialSideEffects"):
        return None

    if not _is_empty_response_assistant_turn(payload_count=payload_count, attempt=attempt):
        return None

    assistant = attempt.get("currentAttemptAssistant") or attempt.get("lastAssistant")
    if (
        isinstance(assistant, dict)
        and assistant.get("stopReason") == "stop"
        and OLLAMA_INCOMPLETE_TURN_PROVIDER_ID_PATTERN.match(_normalize_lower(provider))
        and not _has_positive_output_token_usage(assistant)
    ):
        return None

    if _should_apply_non_visible_turn_retry_guard(
        provider=provider,
        model_id=model_id,
        model_api=model_api,
        execution_contract=execution_contract,
    ) or (
        isinstance(assistant, dict) and is_zero_usage_empty_stop_assistant_turn(assistant)
    ):
        return EMPTY_RESPONSE_RETRY_INSTRUCTION
    return None