"""Proxy stream helpers for LLM calls routed through a gateway server."""

from __future__ import annotations

import json
from copy import deepcopy
from typing import Any, Literal, TypedDict

StopReasonDone = Literal["stop", "length", "toolUse"]
StopReasonError = Literal["aborted", "error"]


class ProxyStreamOptions(TypedDict, total=False):
    temperature: float
    maxTokens: int
    reasoning: Any
    cacheRetention: Any
    sessionId: str
    promptCacheKey: str
    metadata: dict[str, Any]
    transport: str
    thinkingBudgets: Any
    maxRetryDelayMs: int
    authToken: str
    proxyUrl: str


def build_proxy_request_options(options: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "temperature",
        "maxTokens",
        "reasoning",
        "cacheRetention",
        "sessionId",
        "promptCacheKey",
        "metadata",
        "transport",
        "thinkingBudgets",
        "maxRetryDelayMs",
    )
    return {k: options[k] for k in keys if k in options}


def sanitize_proxy_model(model: dict[str, Any]) -> dict[str, Any]:
    safe = dict(model)
    safe.pop("headers", None)
    return safe


def _parse_streaming_json(text: str) -> dict[str, Any]:
    text = text.strip()
    if not text:
        return {}
    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        return {}


def process_proxy_event(
    proxy_event: dict[str, Any],
    partial: dict[str, Any],
) -> dict[str, Any] | None:
    event_type = proxy_event.get("type")
    content = partial.setdefault("content", [])

    if event_type == "start":
        return {"type": "start", "partial": partial}

    if event_type == "text_start":
        idx = int(proxy_event["contentIndex"])
        while len(content) <= idx:
            content.append(None)
        content[idx] = {"type": "text", "text": ""}
        return {"type": "text_start", "contentIndex": idx, "partial": partial}

    if event_type == "text_delta":
        idx = int(proxy_event["contentIndex"])
        block = content[idx]
        if not isinstance(block, dict) or block.get("type") != "text":
            raise ValueError("Received text_delta for non-text content")
        block["text"] = block.get("text", "") + str(proxy_event.get("delta", ""))
        return {
            "type": "text_delta",
            "contentIndex": idx,
            "delta": proxy_event.get("delta", ""),
            "partial": partial,
        }

    if event_type == "text_end":
        idx = int(proxy_event["contentIndex"])
        block = content[idx]
        if not isinstance(block, dict) or block.get("type") != "text":
            raise ValueError("Received text_end for non-text content")
        if "contentSignature" in proxy_event:
            block["textSignature"] = proxy_event["contentSignature"]
        return {
            "type": "text_end",
            "contentIndex": idx,
            "content": block.get("text", ""),
            "partial": partial,
        }

    if event_type == "thinking_start":
        idx = int(proxy_event["contentIndex"])
        while len(content) <= idx:
            content.append(None)
        content[idx] = {"type": "thinking", "thinking": ""}
        return {"type": "thinking_start", "contentIndex": idx, "partial": partial}

    if event_type == "thinking_delta":
        idx = int(proxy_event["contentIndex"])
        block = content[idx]
        if not isinstance(block, dict) or block.get("type") != "thinking":
            raise ValueError("Received thinking_delta for non-thinking content")
        block["thinking"] = block.get("thinking", "") + str(proxy_event.get("delta", ""))
        return {
            "type": "thinking_delta",
            "contentIndex": idx,
            "delta": proxy_event.get("delta", ""),
            "partial": partial,
        }

    if event_type == "thinking_end":
        idx = int(proxy_event["contentIndex"])
        block = content[idx]
        if not isinstance(block, dict) or block.get("type") != "thinking":
            raise ValueError("Received thinking_end for non-thinking content")
        if "contentSignature" in proxy_event:
            block["thinkingSignature"] = proxy_event["contentSignature"]
        return {
            "type": "thinking_end",
            "contentIndex": idx,
            "content": block.get("thinking", ""),
            "partial": partial,
        }

    if event_type == "toolcall_start":
        idx = int(proxy_event["contentIndex"])
        while len(content) <= idx:
            content.append(None)
        content[idx] = {
            "type": "toolCall",
            "id": proxy_event.get("id", ""),
            "name": proxy_event.get("toolName", ""),
            "arguments": {},
            "partialJson": "",
        }
        return {"type": "toolcall_start", "contentIndex": idx, "partial": partial}

    if event_type == "toolcall_delta":
        idx = int(proxy_event["contentIndex"])
        block = content[idx]
        if not isinstance(block, dict) or block.get("type") != "toolCall":
            raise ValueError("Received toolcall_delta for non-toolCall content")
        partial_json = str(block.get("partialJson", "")) + str(proxy_event.get("delta", ""))
        block["partialJson"] = partial_json
        block["arguments"] = _parse_streaming_json(partial_json) or {}
        content[idx] = dict(block)
        return {
            "type": "toolcall_delta",
            "contentIndex": idx,
            "delta": proxy_event.get("delta", ""),
            "partial": partial,
        }

    if event_type == "toolcall_end":
        idx = int(proxy_event["contentIndex"])
        block = content[idx]
        if not isinstance(block, dict) or block.get("type") != "toolCall":
            return None
        block.pop("partialJson", None)
        return {
            "type": "toolcall_end",
            "contentIndex": idx,
            "toolCall": deepcopy(block),
            "partial": partial,
        }

    if event_type == "done":
        partial["stopReason"] = proxy_event.get("reason", "stop")
        if "usage" in proxy_event:
            partial["usage"] = proxy_event["usage"]
        return {
            "type": "done",
            "reason": proxy_event.get("reason", "stop"),
            "message": partial,
        }

    if event_type == "error":
        partial["stopReason"] = proxy_event.get("reason", "error")
        if "errorMessage" in proxy_event:
            partial["errorMessage"] = proxy_event["errorMessage"]
        if "usage" in proxy_event:
            partial["usage"] = proxy_event["usage"]
        return {
            "type": "error",
            "reason": proxy_event.get("reason", "error"),
            "error": partial,
        }

    return None