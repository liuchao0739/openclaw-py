"""Extracts visible delivery evidence from embedded-agent run results."""

from __future__ import annotations

from typing import Any

from openclaw.agents.accepted_session_spawn import has_accepted_session_spawn


def _has_non_empty_string(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _has_non_empty_array(value: object) -> bool:
    return isinstance(value, list) and len(value) > 0


def _has_non_empty_string_array(value: object) -> bool:
    return isinstance(value, list) and any(_has_non_empty_string(x) for x in value)


def _collect_string_values(value: object, output: set[str]) -> None:
    if isinstance(value, str) and value.strip():
        output.add(value.strip())
        return
    if isinstance(value, list):
        for entry in value:
            if isinstance(entry, str) and entry.strip():
                output.add(entry.strip())


def _collect_media_urls_from_record(record: dict[str, Any], output: set[str]) -> None:
    for key in ("mediaUrl", "mediaUrls", "path", "url", "filePath"):
        _collect_string_values(record.get(key), output)
    attachments = record.get("attachments")
    if isinstance(attachments, list):
        for attachment in attachments:
            if isinstance(attachment, dict):
                _collect_media_urls_from_record(attachment, output)


def collect_messaging_tool_delivered_media_urls(result: dict[str, Any]) -> list[str]:
    urls: set[str] = set()
    _collect_string_values(result.get("messagingToolSentMediaUrls"), urls)
    targets = result.get("messagingToolSentTargets")
    if isinstance(targets, list):
        for target in targets:
            if isinstance(target, dict):
                _collect_media_urls_from_record(target, urls)
    return list(urls)


def collect_delivered_media_urls(result: dict[str, Any]) -> list[str]:
    urls: set[str] = set()
    payloads = result.get("payloads")
    if isinstance(payloads, list):
        for payload in payloads:
            if isinstance(payload, dict):
                _collect_media_urls_from_record(payload, urls)
    for url in collect_messaging_tool_delivered_media_urls(result):
        urls.add(url)
    return list(urls)


def _has_agent_delivery_evidence_shape(value: object) -> bool:
    if not isinstance(value, dict):
        return False
    keys = (
        "payloads",
        "deliveryStatus",
        "didSendViaMessagingTool",
        "messagingToolSentTexts",
        "messagingToolSentMediaUrls",
        "messagingToolSentTargets",
        "acceptedSessionSpawns",
        "successfulCronAdds",
        "meta",
    )
    return any(k in value for k in keys)


def get_gateway_agent_result(response: object) -> dict[str, Any] | None:
    if not isinstance(response, dict):
        return None
    candidate = response if _has_agent_delivery_evidence_shape(response) else response.get("result")
    if isinstance(candidate, dict) and _has_agent_delivery_evidence_shape(candidate):
        return candidate
    return None


def has_visible_agent_payload(
    result: dict[str, Any],
    *,
    include_error_payloads: bool = True,
    include_reasoning_payloads: bool = True,
) -> bool:
    payloads = result.get("payloads")
    if not isinstance(payloads, list):
        return False
    for payload in payloads:
        if not isinstance(payload, dict):
            continue
        if not include_error_payloads and payload.get("isError") is True:
            continue
        if not include_reasoning_payloads and payload.get("isReasoning") is True:
            continue
        if (
            _has_non_empty_string(payload.get("text"))
            or _has_non_empty_string(payload.get("mediaUrl"))
            or _has_non_empty_string_array(payload.get("mediaUrls"))
            or payload.get("presentation")
            or payload.get("interactive")
            or payload.get("channelData")
        ):
            return True
    return False


def has_committed_messaging_tool_delivery_evidence(result: dict[str, Any]) -> bool:
    return (
        _has_non_empty_string_array(result.get("messagingToolSentTexts"))
        or _has_non_empty_string_array(result.get("messagingToolSentMediaUrls"))
        or _has_non_empty_array(result.get("messagingToolSentTargets"))
    )


def has_messaging_tool_delivery_evidence(result: dict[str, Any]) -> bool:
    return result.get("didSendViaMessagingTool") is True or has_committed_messaging_tool_delivery_evidence(
        result
    )


def has_committed_outbound_delivery_evidence(result: dict[str, Any]) -> bool:
    spawns = result.get("acceptedSessionSpawns")
    cron = result.get("successfulCronAdds")
    return (
        has_messaging_tool_delivery_evidence(result)
        or (isinstance(spawns, list) and has_accepted_session_spawn(spawns))
        or (isinstance(cron, (int, float)) and cron == cron and cron > 0)
    )


def has_outbound_delivery_evidence(result: dict[str, Any]) -> bool:
    meta = result.get("meta")
    calls = None
    if isinstance(meta, dict):
        tool_summary = meta.get("toolSummary")
        if isinstance(tool_summary, dict):
            calls = tool_summary.get("calls")
    return has_committed_outbound_delivery_evidence(result) or (
        isinstance(calls, (int, float)) and calls == calls and calls > 0
    )


def get_agent_command_delivery_failure(result: dict[str, Any]) -> str | None:
    delivery = result.get("deliveryStatus")
    if not isinstance(delivery, dict):
        return None
    status = delivery.get("status")
    if status not in ("failed", "partial_failed"):
        return None
    message = delivery.get("errorMessage")
    if _has_non_empty_string(message):
        return message.strip()
    return "agent delivery partially failed" if status == "partial_failed" else "agent delivery failed"