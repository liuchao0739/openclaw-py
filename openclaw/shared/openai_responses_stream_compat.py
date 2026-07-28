"""OpenAI responses stream compat for text content part types and delta events."""

from __future__ import annotations

from typing import Any


OPENAI_RESPONSES_OUTPUT_TEXT_CONTENT_PART_TYPE = "output_text"
AZURE_RESPONSES_TEXT_CONTENT_PART_TYPE = "text"
OPENAI_RESPONSES_OUTPUT_TEXT_DELTA_EVENT_TYPE = "response.output_text.delta"
AZURE_RESPONSES_TEXT_DELTA_EVENT_TYPE = "response.text.delta"


def is_responses_text_content_part_type(type_value: Any) -> bool:
    return type_value in (
        OPENAI_RESPONSES_OUTPUT_TEXT_CONTENT_PART_TYPE,
        AZURE_RESPONSES_TEXT_CONTENT_PART_TYPE,
    )


def is_responses_text_delta_event_type(type_value: Any) -> bool:
    return type_value in (
        OPENAI_RESPONSES_OUTPUT_TEXT_DELTA_EVENT_TYPE,
        AZURE_RESPONSES_TEXT_DELTA_EVENT_TYPE,
    )


def is_azure_responses_text_delta_event_type(type_value: Any) -> bool:
    return type_value == AZURE_RESPONSES_TEXT_DELTA_EVENT_TYPE


def is_azure_responses_text_delta_event(event: dict[str, Any]) -> bool:
    return is_azure_responses_text_delta_event_type(event.get("type")) and isinstance(event.get("delta"), str)


def resolve_responses_message_snapshot_collapse(
    prior: dict[str, Any] | None,
    next_text: str,
    next_phase: str | None = None,
) -> dict[str, Any]:
    if not prior or not prior.get("text") or not next_text or prior.get("phase") != next_phase:
        return {"kind": "keep"}
    if len(next_text) > len(prior["text"]) and next_text.startswith(prior["text"]):
        return {"kind": "extend", "text": next_text}
    return {"kind": "keep"}
