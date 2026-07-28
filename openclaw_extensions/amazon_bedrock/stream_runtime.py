from __future__ import annotations

import os
import re
from typing import Any, Callable

from openclaw.plugin_sdk.llm import (
    Api,
    AssistantMessage,
    AssistantMessageEvent,
    AssistantMessageEventStream,
    CacheRetention,
    Context,
    Model,
    SimpleStreamOptions,
    StopReason,
    StreamFunction,
    StreamOptions,
    TextContent,
    ThinkingContent,
    ThinkingLevel,
    Tool,
    ToolCall,
    ToolResultMessage,
    adjust_max_tokens_for_thinking,
    build_base_options,
    calculate_cost,
    clamp_reasoning,
    create_http_proxy_agents_for_target,
    parse_streaming_json,
    sanitize_surrogates,
    transform_messages,
)
from openclaw.plugin_sdk.provider_model_shared import (
    resolve_claude_fable5_model_identity,
    resolve_claude_model_identity,
    supports_claude_adaptive_thinking,
    supports_claude_native_xhigh_effort,
)
from openclaw.plugin_sdk.provider_stream_shared import (
    apply_anthropic_refusal,
    create_deferred_event_buffer,
    notify_llm_request_activity,
)
from openclaw_extensions.amazon_bedrock.bedrock_options import (
    supports_bedrock_prompt_caching,
)
from openclaw_extensions.amazon_bedrock.thinking_policy import (
    supports_bedrock_native_max_effort,
)


def _uses_claude_fable5_bedrock_contract(model: Model) -> bool:
    return resolve_claude_fable5_model_identity(model) is not None


def _read_bedrock_stop_details(fields: Any) -> Any:
    if fields is None or not isinstance(fields, dict):
        return None
    record = fields
    return record.get("stop_details", record.get("stopDetails"))


def _normalize_fable_tool_choice(tool_choice: Any) -> Any:
    if tool_choice == "any" or (isinstance(tool_choice, dict) and tool_choice.get("type") == "tool"):
        return "auto"
    return tool_choice


_BEDROCK_ERROR_PREFIXES: dict[str, str] = {
    "InternalServerException": "Internal server error",
    "ModelStreamErrorException": "Model stream error",
    "ValidationException": "Validation error",
    "ThrottlingException": "Throttling error",
    "ServiceUnavailableException": "Service unavailable",
}


def _format_bedrock_error(error: Any) -> str:
    message = str(error) if not isinstance(error, str) else error
    if hasattr(error, "name") and hasattr(error, "message"):
        prefix = _BEDROCK_ERROR_PREFIXES.get(error.name, error.name)
        return f"{prefix}: {error.message}"
    return message


def _get_configured_bedrock_region(options: dict[str, Any]) -> str | None:
    if not isinstance(os.environ, dict):
        return options.get("region")
    return options.get("region") or os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION")


def _has_configured_bedrock_profile(options: dict[str, Any]) -> bool:
    if options.get("profile"):
        return True
    if not isinstance(os.environ, dict):
        return False
    return bool(os.environ.get("AWS_PROFILE"))


def _get_standard_bedrock_endpoint_region(base_url: str | None) -> str | None:
    if not base_url:
        return None
    try:
        from urllib.parse import urlparse
        parsed = urlparse(base_url)
        hostname = parsed.hostname or ""
        match = re.match(r"^bedrock-runtime(?:-fips)?\.([a-z0-9-]+)\.amazonaws\.com(?:\.cn)?$", hostname)
        return match.group(1) if match else None
    except Exception:
        return None


def _should_use_explicit_bedrock_endpoint(
    base_url: str,
    configured_region: str | None,
    has_configured_profile: bool,
) -> bool:
    endpoint_region = _get_standard_bedrock_endpoint_region(base_url)
    if endpoint_region is None:
        return True
    return not configured_region and not has_configured_profile


def _is_gov_cloud_bedrock_target(model: Model, options: dict[str, Any]) -> bool:
    region = _get_configured_bedrock_region(options)
    if region and region.lower().startswith("us-gov-"):
        return True
    model_id = (model.get("id") or "").lower()
    return model_id.startswith("us-gov.") or model_id.startswith("arn:aws-us-gov:")


def _resolve_cache_retention(cache_retention: CacheRetention | None) -> CacheRetention:
    if cache_retention is not None:
        return cache_retention
    if os.environ.get("OPENCLAW_CACHE_RETENTION") == "long":
        return "long"
    return "short"


def _is_anthropic_claude_model(model: Model) -> bool:
    if _uses_claude_fable5_bedrock_contract(model):
        return True
    model_id = resolve_claude_model_identity(model)
    if model_id.startswith("claude-"):
        return True
    id_lower = (model.get("id") or "").lower()
    name_lower = (model.get("name") or "").lower()
    return (
        "anthropic.claude" in id_lower
        or "anthropic/claude" in id_lower
        or "anthropic.claude" in name_lower
        or "anthropic/claude" in name_lower
        or "claude" in name_lower
    )


def _resolve_claude_profile_name_model_id(model_name: str | None) -> str | None:
    if not model_name:
        return None
    normalized = model_name.strip().lower().replace(" ", "-").replace("_", "-").replace(".", "-").replace(":", "-")
    if "claude" not in normalized:
        return None
    match = re.search(r"(?:fable-5|mythos-preview|opus-4-(?:6|7|8)|sonnet-4-6)(?:$|-)", normalized)
    if match:
        family = match.group(0)
        return f"claude-{family.rstrip('-')}"
    return None


def _is_claude_mythos_preview_model_id(model_id: str | None) -> bool:
    if not model_id:
        return False
    normalized = model_id.strip().lower().replace(" ", "-").replace("_", "-").replace(".", "-").replace(":", "-")
    return bool(re.search(r"(?:^|-)claude-mythos-preview(?=$|[^a-z0-9])", normalized))


def _supports_adaptive_thinking(model: Model) -> bool:
    profile_model_id = _resolve_claude_profile_name_model_id(model.get("name"))
    return (
        supports_claude_adaptive_thinking(model)
        or supports_claude_adaptive_thinking({"id": profile_model_id} if profile_model_id else {})
        or _is_claude_mythos_preview_model_id(resolve_claude_model_identity(model))
        or _is_claude_mythos_preview_model_id(profile_model_id)
    )


def _requires_mandatory_adaptive_thinking(model: Model) -> bool:
    profile_model_id = _resolve_claude_profile_name_model_id(model.get("name"))
    return (
        _is_claude_mythos_preview_model_id(resolve_claude_model_identity(model))
        or _is_claude_mythos_preview_model_id(profile_model_id)
    )


def _supports_native_xhigh_effort(model: Model) -> bool:
    profile_model_id = _resolve_claude_profile_name_model_id(model.get("name"))
    return (
        supports_claude_native_xhigh_effort(model)
        or supports_claude_native_xhigh_effort({"id": profile_model_id} if profile_model_id else {})
    )


def _supports_native_max_effort(model: Model) -> bool:
    profile_model_id = _resolve_claude_profile_name_model_id(model.get("name"))
    return (
        supports_bedrock_native_max_effort(model.get("id"), model.get("params"))
        or supports_bedrock_native_max_effort(profile_model_id or "")
    )


def _supports_prompt_caching(model: Model) -> bool:
    return (
        _uses_claude_fable5_bedrock_contract(model)
        or supports_bedrock_prompt_caching(model.get("id", ""), model.get("name"))
        or supports_bedrock_prompt_caching(resolve_claude_model_identity(model), model.get("name"))
    )


def _supports_thinking_signature(model: Model) -> bool:
    return _is_anthropic_claude_model(model)


def _map_thinking_level_to_effort(
    model: Model,
    level: ThinkingLevel | None,
) -> str:
    mapped = model.get("thinkingLevelMap", {}) if isinstance(model.get("thinkingLevelMap"), dict) else {}
    if level and level in mapped:
        result = mapped[level]
        if isinstance(result, str):
            return result
    if level in ("xhigh", "max") and mapped.get(level) is None:
        return "high"

    if level == "minimal" or level == "low":
        return "low"
    if level == "medium":
        return "medium"
    if level == "high":
        return "high"
    if level == "xhigh":
        return "xhigh" if _supports_native_xhigh_effort(model) else "high"
    if level == "max":
        return "max" if _supports_native_max_effort(model) else "high"
    return "high"


def _build_system_prompt(
    system_prompt: str | None,
    model: Model,
    cache_retention: CacheRetention,
) -> list[dict[str, Any]] | None:
    if not system_prompt:
        return None

    blocks: list[dict[str, Any]] = [{"text": sanitize_surrogates(system_prompt)}]

    if cache_retention != "none" and _supports_prompt_caching(model):
        cache_point: dict[str, Any] = {"cachePoint": {"type": "default"}}
        if cache_retention == "long":
            cache_point["cachePoint"]["ttl"] = "1h"
        blocks.append(cache_point)

    return blocks


def _normalize_tool_call_id(tool_id: str) -> str:
    sanitized = re.sub(r"[^a-zA-Z0-9_-]", "_", tool_id)
    return sanitized[:64] if len(sanitized) > 64 else sanitized


def _convert_messages(
    context: Context,
    model: Model,
    cache_retention: CacheRetention,
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    transformed_messages = transform_messages(context.get("messages", []), model, _normalize_tool_call_id)

    i = 0
    while i < len(transformed_messages):
        m = transformed_messages[i]
        role = m.get("role", "")

        if role == "user":
            content_blocks: list[dict[str, Any]] = []
            msg_content = m.get("content", "")
            if isinstance(msg_content, str):
                content_blocks.append({"text": sanitize_surrogates(msg_content)})
            elif isinstance(msg_content, list):
                for c in msg_content:
                    if c.get("type") == "text":
                        content_blocks.append({"text": sanitize_surrogates(c.get("text", ""))})
                    elif c.get("type") == "image":
                        content_blocks.append({
                            "image": _create_image_block(c.get("mimeType", ""), c.get("data", "")),
                        })
            if not content_blocks:
                i += 1
                continue
            result.append({"role": "user", "content": content_blocks})

        elif role == "assistant":
            msg_content = m.get("content", [])
            if not isinstance(msg_content, list) or len(msg_content) == 0:
                i += 1
                continue
            content_blocks: list[dict[str, Any]] = []
            for c in msg_content:
                c_type = c.get("type", "")
                if c_type == "text":
                    text_val = c.get("text", "")
                    if text_val.strip():
                        content_blocks.append({"text": sanitize_surrogates(text_val)})
                elif c_type == "toolCall":
                    content_blocks.append({
                        "toolUse": {
                            "toolUseId": c.get("id", ""),
                            "name": c.get("name", ""),
                            "input": c.get("arguments", {}),
                        },
                    })
                elif c_type == "thinking":
                    thinking_signature = c.get("thinkingSignature", "")
                    normalized_signature = thinking_signature.strip() if thinking_signature else ""
                    supports_sig = _supports_thinking_signature(model)
                    has_native_sig = supports_sig and normalized_signature and normalized_signature != "reasoning_content"

                    thinking_text = c.get("thinking", "")
                    if not thinking_text.strip() and not has_native_sig:
                        continue

                    if supports_sig:
                        if normalized_signature == "reasoning_content":
                            continue
                        if not thinking_signature or not normalized_signature:
                            content_blocks.append({"text": sanitize_surrogates(thinking_text)})
                        else:
                            content_blocks.append({
                                "reasoningContent": {
                                    "reasoningText": {
                                        "text": thinking_text,
                                        "signature": thinking_signature,
                                    },
                                },
                            })
                    else:
                        content_blocks.append({"text": sanitize_surrogates(thinking_text)})

            if not content_blocks:
                i += 1
                continue
            result.append({"role": "assistant", "content": content_blocks})

        elif role == "toolResult":
            _tool_content = [
                {
                    "text": sanitize_surrogates(c.get("text", ""))
                    if c.get("type") != "image"
                    else {
                        "image": _create_image_block(c.get("mimeType", ""), c.get("data", "")),
                    }
                }
                for c in (m.get("content", []) or [])
            ]
            tool_results: list[dict[str, Any]] = [{
                "toolResult": {
                    "toolUseId": m.get("toolCallId", ""),
                    "content": _tool_content,
                },
                "status": "error" if m.get("isError") else "success",
            }]

            j = i + 1
            while j < len(transformed_messages) and transformed_messages[j].get("role") == "toolResult":
                next_msg = transformed_messages[j]
                _next_content = [
                    {
                        "text": sanitize_surrogates(c.get("text", ""))
                        if c.get("type") != "image"
                        else {
                            "image": _create_image_block(c.get("mimeType", ""), c.get("data", "")),
                        }
                    }
                    for c in (next_msg.get("content", []) or [])
                ]
                tool_results.append({
                    "toolResult": {
                        "toolUseId": next_msg.get("toolCallId", ""),
                        "content": _next_content,
                    },
                    "status": "error" if next_msg.get("isError") else "success",
                })
                j += 1

            i = j - 1
            result.append({"role": "user", "content": tool_results})

        i += 1

    if cache_retention != "none" and _supports_prompt_caching(model) and result:
        last_msg = result[-1]
        if last_msg.get("role") == "user" and isinstance(last_msg.get("content"), list):
            cache_point: dict[str, Any] = {"cachePoint": {"type": "default"}}
            if cache_retention == "long":
                cache_point["cachePoint"]["ttl"] = "1h"
            last_msg["content"].append(cache_point)

    return result


def _convert_tool_config(
    tools: list[Tool] | None,
    tool_choice: Any,
) -> dict[str, Any] | None:
    if not tools or not tool_choice or tool_choice == "none":
        return None

    bedrock_tools: list[dict[str, Any]] = []
    for tool in tools:
        tool_spec: dict[str, Any] = {
            "name": tool.get("name", ""),
            "description": tool.get("description", ""),
            "inputSchema": {"json": tool.get("parameters", {})},
        }
        bedrock_tools.append({"toolSpec": tool_spec})

    bedrock_tool_choice: dict[str, Any] | None = None
    if tool_choice == "auto":
        bedrock_tool_choice = {"auto": {}}
    elif tool_choice == "any":
        bedrock_tool_choice = {"any": {}}
    elif isinstance(tool_choice, dict) and tool_choice.get("type") == "tool":
        bedrock_tool_choice = {"tool": {"name": tool_choice.get("name", "")}}

    return {"tools": bedrock_tools, "toolChoice": bedrock_tool_choice}


def _map_stop_reason(reason: str | None) -> StopReason:
    if reason in ("end_turn", "stop_sequence", "END_TURN", "STOP_SEQUENCE"):
        return "stop"
    if reason in ("max_tokens", "model_context_window_exceeded", "MAX_TOKENS", "MODEL_CONTEXT_WINDOW_EXCEEDED"):
        return "length"
    if reason in ("tool_use", "TOOL_USE"):
        return "toolUse"
    return "error"


def _build_additional_model_request_fields(
    model: Model,
    options: dict[str, Any],
) -> dict[str, Any] | None:
    reasoning = options.get("reasoning")
    if not reasoning or (
        not model.get("reasoning")
        and not _uses_claude_fable5_bedrock_contract(model)
        and not _supports_adaptive_thinking(model)
    ):
        return None

    if _is_anthropic_claude_model(model):
        display = None
        if not _is_gov_cloud_bedrock_target(model, options):
            display = options.get("thinkingDisplay", "summarized")

        if _supports_adaptive_thinking(model):
            result: dict[str, Any] = {
                "thinking": {"type": "adaptive"},
                "output_config": {"effort": _map_thinking_level_to_effort(model, reasoning)},
            }
            if display is not None:
                result["thinking"]["display"] = display
            return result

        default_budgets: dict[str, int] = {
            "minimal": 1024,
            "low": 2048,
            "medium": 8192,
            "high": 16384,
            "xhigh": 16384,
            "max": 16384,
        }
        level = reasoning if reasoning != "xhigh" else "high"
        budget = (
            options.get("thinkingBudgets", {}).get(level)
            if isinstance(options.get("thinkingBudgets"), dict)
            else None
        ) or default_budgets.get(reasoning, 16384)

        result = {
            "thinking": {
                "type": "enabled",
                "budget_tokens": budget,
            },
        }
        if display is not None:
            result["thinking"]["display"] = display

        if not _supports_adaptive_thinking(model) and options.get("interleavedThinking", True):
            result["anthropic_beta"] = ["interleaved-thinking-2025-05-14"]

        return result

    return None


def _create_image_block(mime_type: str, data: str) -> dict[str, Any]:
    from base64 import b64decode
    format_map = {
        "image/jpeg": "jpeg",
        "image/jpg": "jpeg",
        "image/png": "png",
        "image/gif": "gif",
        "image/webp": "webp",
    }
    fmt = format_map.get(mime_type)
    if fmt is None:
        raise ValueError(f"Unknown image type: {mime_type}")
    bytes_data = b64decode(data)
    return {"source": bytes_data, "format": fmt}


def stream_bedrock(
    model: Model,
    context: Context,
    options: dict[str, Any] | None = None,
) -> AssistantMessageEventStream:
    if options is None:
        options = {}
    stream = AssistantMessageEventStream()

    import asyncio

    async def _run():
        output: AssistantMessage = {
            "role": "assistant",
            "content": [],
            "api": "bedrock-converse-stream",
            "provider": model.get("provider", ""),
            "model": model.get("id", ""),
            "usage": {
                "input": 0,
                "output": 0,
                "cacheRead": 0,
                "cacheWrite": 0,
                "totalTokens": 0,
                "cost": {"input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0, "total": 0},
            },
            "stopReason": "stop",
            "timestamp": int(__import__("time").time() * 1000),
        }

        blocks: list[dict[str, Any]] = output["content"]
        fable5 = _uses_claude_fable5_bedrock_contract(model)
        refusal_buffer = None
        if fable5:
            refusal_buffer = create_deferred_event_buffer(stream, lambda: notify_llm_request_activity(options.get("signal")))
        event_sink = refusal_buffer or stream

        config: dict[str, Any] = {
            "profile": options.get("profile"),
        }

        configured_region = _get_configured_bedrock_region(options)
        has_configured_profile = _has_configured_bedrock_profile(options)
        endpoint_region = _get_standard_bedrock_endpoint_region(model.get("baseUrl"))
        use_explicit_endpoint = _should_use_explicit_bedrock_endpoint(
            model.get("baseUrl", ""),
            configured_region,
            has_configured_profile,
        )

        if use_explicit_endpoint:
            config["endpoint"] = model.get("baseUrl")

        bearer_token = options.get("bearerToken") or os.environ.get("AWS_BEARER_TOKEN_BEDROCK")
        use_bearer_token = bearer_token is not None and os.environ.get("AWS_BEDROCK_SKIP_AUTH") != "1"

        if isinstance(os.environ, dict) and (os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION") or True):
            if configured_region:
                config["region"] = configured_region
            elif endpoint_region and use_explicit_endpoint:
                config["region"] = endpoint_region
            elif not has_configured_profile:
                config["region"] = "us-east-1"

            if os.environ.get("AWS_BEDROCK_SKIP_AUTH") == "1":
                config["credentials"] = {
                    "accessKeyId": "dummy-access-key",
                    "secretAccessKey": "dummy-secret-key",
                }

            proxy_agents = create_http_proxy_agents_for_target(model.get("baseUrl"))
            if proxy_agents:
                from smithy_node_http_handler import NodeHttpHandler
                config["requestHandler"] = NodeHttpHandler(proxy_agents)
            elif os.environ.get("AWS_BEDROCK_FORCE_HTTP1") == "1":
                from smithy_node_http_handler import NodeHttpHandler
                config["requestHandler"] = NodeHttpHandler()

        if use_bearer_token:
            config["token"] = {"token": bearer_token}
            config["authSchemePreference"] = ["httpBearerAuth"]

        try:
            from bedrock_runtime import BedrockRuntimeClient, ConverseStreamCommand
            client = BedrockRuntimeClient(config)

            cache_retention = _resolve_cache_retention(options.get("cacheRetention"))
            additional_fields = _build_additional_model_request_fields(model, options)
            thinking = None
            if additional_fields and isinstance(additional_fields, dict):
                thinking = additional_fields.get("thinking")
            sends_adaptive_thinking = (
                thinking is not None
                and isinstance(thinking, dict)
                and thinking.get("type") == "adaptive"
            )

            command_input: dict[str, Any] = {
                "modelId": model.get("id", ""),
                "messages": _convert_messages(context, model, cache_retention),
                "system": _build_system_prompt(context.get("systemPrompt"), model, cache_retention),
                "inferenceConfig": {},
                "toolConfig": _convert_tool_config(
                    context.get("tools"),
                    _normalize_fable_tool_choice(options.get("toolChoice")) if fable5 else options.get("toolChoice"),
                ),
            }

            if options.get("maxTokens") is not None:
                command_input["inferenceConfig"]["maxTokens"] = options["maxTokens"]
            if options.get("temperature") is not None and not sends_adaptive_thinking:
                command_input["inferenceConfig"]["temperature"] = options["temperature"]
            if additional_fields is not None:
                command_input["additionalModelRequestFields"] = additional_fields
            if fable5:
                command_input["additionalModelResponseFieldPaths"] = ["/stop_details"]
            if options.get("requestMetadata") is not None:
                command_input["requestMetadata"] = options["requestMetadata"]

            on_payload = options.get("onPayload")
            if callable(on_payload):
                next_input = await on_payload(command_input, model)
                if next_input is not None:
                    command_input = next_input

            command = ConverseStreamCommand(command_input)
            response = client.send(command, {"abortSignal": options.get("signal")} if options.get("signal") else None)

            http_status_code = response.get("$metadata", {}).get("httpStatusCode")
            if http_status_code is not None:
                response_headers: dict[str, str] = {}
                request_id = response.get("$metadata", {}).get("requestId")
                if request_id:
                    response_headers["x-amzn-requestid"] = request_id
                on_response = options.get("onResponse")
                if callable(on_response):
                    await on_response({"status": http_status_code, "headers": response_headers}, model)

            saw_message_stop = False
            for item in response.get("stream", []):
                if item.get("messageStart"):
                    start_data = item["messageStart"]
                    if start_data.get("role") != "assistant":
                        raise ValueError("Unexpected assistant message start but got user message start instead")
                    event_sink.push({"type": "start", "partial": output})

                elif item.get("contentBlockStart"):
                    content_block_start = item["contentBlockStart"]
                    idx = content_block_start.get("contentBlockIndex", 0)
                    start_data = content_block_start.get("start", {})
                    if start_data.get("toolUse"):
                        block: dict[str, Any] = {
                            "type": "toolCall",
                            "id": start_data["toolUse"].get("toolUseId", ""),
                            "name": start_data["toolUse"].get("name", ""),
                            "arguments": {},
                            "index": idx,
                            "partialJson": "",
                        }
                        blocks.append(block)
                        event_sink.push({
                            "type": "toolcall_start",
                            "contentIndex": len(blocks) - 1,
                            "partial": output,
                        })

                elif item.get("contentBlockDelta"):
                    delta = item["contentBlockDelta"]
                    idx = delta.get("contentBlockIndex", 0)
                    block = next((b for b in blocks if b.get("index") == idx), None)

                    if delta.get("text") is not None:
                        if block is None:
                            block = {"type": "text", "text": "", "index": idx}
                            blocks.append(block)
                            event_sink.push({
                                "type": "text_start",
                                "contentIndex": len(blocks) - 1,
                                "partial": output,
                            })
                        if block.get("type") == "text":
                            block["text"] += delta["text"]
                            event_sink.push({
                                "type": "text_delta",
                                "contentIndex": idx,
                                "delta": delta["text"],
                                "partial": output,
                            })

                    elif delta.get("toolUse") and block and block.get("type") == "toolCall":
                        block["partialJson"] = (block.get("partialJson", "") or "") + (delta["toolUse"].get("input", "") or "")
                        block["arguments"] = parse_streaming_json(block["partialJson"])
                        event_sink.push({
                            "type": "toolcall_delta",
                            "contentIndex": idx,
                            "delta": delta["toolUse"].get("input", "") or "",
                            "partial": output,
                        })

                    elif delta.get("reasoningContent"):
                        thinking_block = block
                        thinking_idx = idx

                        if thinking_block is None:
                            thinking_block = {
                                "type": "thinking",
                                "thinking": "",
                                "thinkingSignature": "",
                                "index": idx,
                            }
                            blocks.append(thinking_block)
                            thinking_idx = len(blocks) - 1
                            event_sink.push({
                                "type": "thinking_start",
                                "contentIndex": thinking_idx,
                                "partial": output,
                            })

                        if thinking_block.get("type") == "thinking":
                            rc = delta["reasoningContent"]
                            if rc.get("text"):
                                thinking_block["thinking"] += rc["text"]
                                event_sink.push({
                                    "type": "thinking_delta",
                                    "contentIndex": thinking_idx,
                                    "delta": rc["text"],
                                    "partial": output,
                                })
                            if rc.get("signature"):
                                thinking_block["thinkingSignature"] = (
                                    (thinking_block.get("thinkingSignature", "") or "") + rc["signature"]
                                )

                elif item.get("contentBlockStop"):
                    idx = item["contentBlockStop"].get("contentBlockIndex", 0)
                    block = next((b for b in blocks if b.get("index") == idx), None)
                    if block is None:
                        continue
                    if "index" in block:
                        del block["index"]

                    block_type = block.get("type", "")
                    if block_type == "text":
                        event_sink.push({
                            "type": "text_end",
                            "contentIndex": idx,
                            "content": block.get("text", ""),
                            "partial": output,
                        })
                    elif block_type == "thinking":
                        event_sink.push({
                            "type": "thinking_end",
                            "contentIndex": idx,
                            "content": block.get("thinking", ""),
                            "partial": output,
                        })
                    elif block_type == "toolCall":
                        block["arguments"] = parse_streaming_json(block.get("partialJson", "") or "")
                        if "partialJson" in block:
                            del block["partialJson"]
                        event_sink.push({
                            "type": "toolcall_end",
                            "contentIndex": idx,
                            "toolCall": block,
                            "partial": output,
                        })

                elif item.get("messageStop"):
                    saw_message_stop = True
                    stop_reason = item["messageStop"].get("stopReason", "")
                    if stop_reason == "refusal":
                        apply_anthropic_refusal(
                            output,
                            _read_bedrock_stop_details(item["messageStop"].get("additionalModelResponseFields")),
                            model.get("provider", ""),
                        )
                    else:
                        output["stopReason"] = _map_stop_reason(stop_reason)

                elif item.get("metadata"):
                    metadata = item["metadata"]
                    usage = metadata.get("usage", {})
                    if usage:
                        output["usage"]["input"] = usage.get("inputTokens", 0)
                        output["usage"]["output"] = usage.get("outputTokens", 0)
                        output["usage"]["cacheRead"] = usage.get("cacheReadInputTokens", 0)
                        output["usage"]["cacheWrite"] = usage.get("cacheWriteInputTokens", 0)
                        output["usage"]["totalTokens"] = usage.get("totalTokens", 0) or (
                            output["usage"]["input"] + output["usage"]["output"]
                        )
                        calculate_cost(model, output["usage"])

                elif item.get("internalServerException"):
                    raise item["internalServerException"]
                elif item.get("modelStreamErrorException"):
                    raise item["modelStreamErrorException"]
                elif item.get("validationException"):
                    raise item["validationException"]
                elif item.get("throttlingException"):
                    raise item["throttlingException"]
                elif item.get("serviceUnavailableException"):
                    raise item["serviceUnavailableException"]

            if refusal_buffer and not saw_message_stop:
                raise ValueError("Bedrock stream ended before messageStop")
            if options.get("signal") and options["signal"].get("aborted"):
                raise ValueError("Request was aborted")

            if output.get("stopReason") == "error" or output.get("stopReason") == "aborted":
                raise ValueError(output.get("errorMessage", "An unknown error occurred"))

            if refusal_buffer:
                refusal_buffer.flush()
            stream.push({"type": "done", "reason": output.get("stopReason", ""), "message": output})
            stream.end()

        except Exception as e:
            for block in output["content"]:
                if "index" in block:
                    del block["index"]
                if "partialJson" in block:
                    del block["partialJson"]
            if refusal_buffer:
                refusal_buffer.discard()
                output["content"] = []
            output["stopReason"] = "aborted" if (options.get("signal") and options["signal"].get("aborted")) else "error"
            output["errorMessage"] = _format_bedrock_error(e)
            stream.push({"type": "error", "reason": output["stopReason"], "error": output})
            stream.end()

    asyncio.ensure_future(_run())
    return stream


def _resolve_simple_bedrock_options(
    model: Model,
    options: SimpleStreamOptions | None,
) -> dict[str, Any]:
    base = build_base_options(model, options, None)
    if _uses_claude_fable5_bedrock_contract(model):
        return {
            **base,
            "reasoning": (options or {}).get("reasoning", "high"),
            "thinkingBudgets": (options or {}).get("thinkingBudgets"),
        }
    reasoning = (options or {}).get("reasoning")
    if not reasoning:
        if _is_anthropic_claude_model(model) and _requires_mandatory_adaptive_thinking(model):
            reasoning = "high"
        return {**base, "reasoning": reasoning}

    if _is_anthropic_claude_model(model):
        if _supports_adaptive_thinking(model):
            return {
                **base,
                "reasoning": reasoning,
                "thinkingBudgets": (options or {}).get("thinkingBudgets"),
            }

        adjusted = adjust_max_tokens_for_thinking(
            base.get("maxTokens"),
            model.get("maxTokens"),
            reasoning,
            (options or {}).get("thinkingBudgets"),
        )
        return {
            **base,
            "maxTokens": adjusted.get("maxTokens"),
            "reasoning": reasoning,
            "thinkingBudgets": {
                **(options or {}).get("thinkingBudgets", {}),
                clamp_reasoning(reasoning): adjusted.get("thinkingBudget"),
            },
        }

    return {
        **base,
        "reasoning": reasoning,
        "thinkingBudgets": (options or {}).get("thinkingBudgets"),
    }


def stream_simple_bedrock(
    model: Model,
    context: Context,
    options: SimpleStreamOptions | None = None,
) -> AssistantMessageEventStream:
    return stream_bedrock(model, context, _resolve_simple_bedrock_options(model, options))


__all__ = [
    "stream_bedrock",
    "stream_simple_bedrock",
]